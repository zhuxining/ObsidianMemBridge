//! Incremental Markdown -> LanceDB projection.

use crate::document::parse::{DocumentRead, read_document_if_changed};
use crate::document::types::{Fingerprint, PathScope, Slice};
use crate::error::{AgentWikiError, Result};
use crate::projection::types::SyncReport;
use crate::{
    document,
    document::relation,
    projection::{
        LanceIndex,
        embedding::Embedder,
        lance::{DocumentReplacement, embedding_input_hash},
    },
};
use camino::Utf8Path;
use fs2::FileExt;
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashMap};
use std::sync::{Arc, Mutex, OnceLock};

const EMBEDDING_IDENTITY: &str = "BAAI/bge-small-zh-v1.5";
/// Bounded local inference batch; keeps peak memory predictable on large imports.
const EMBED_BATCH_SIZE: usize = 32;
/// Bound source predicates and pending document data. A single oversized
/// document remains a one-item batch so existing document limits do not shrink.
const WRITE_BATCH_PATHS: usize = 32;
const WRITE_BATCH_ROWS: usize = 4_096;

pub struct Projection {
    pub root: camino::Utf8PathBuf,
    pub index: LanceIndex,
    /// Configured model identity, or `None` when semantic search is disabled.
    pub embedding_model: Option<&'static str>,
    embedder: OnceLock<Arc<Mutex<Embedder>>>,
    embedding_error: Mutex<Option<String>>,
    lock_path: camino::Utf8PathBuf,
    /// Set when opening finds history or a write commits, avoiding cleanup on no-op queries.
    prune_pending: bool,
}

struct PreparedReplacement {
    replacement: DocumentReplacement,
    moved: bool,
    vectors_ready: usize,
    vectors_reused: usize,
    vectors_pending: usize,
}

struct VectorOutcome {
    vectors: Vec<Option<Vec<f32>>>,
    ready: usize,
    reused: usize,
    pending: usize,
}

impl Projection {
    pub async fn assemble_with_embedding(
        root: &Utf8Path,
        index_dir: &Utf8Path,
        model: Option<&str>,
    ) -> Result<Self> {
        if model.is_some_and(|m| m != EMBEDDING_IDENTITY) {
            return Err(AgentWikiError::Config("unsupported embedding model".into()));
        }
        tokio::fs::create_dir_all(index_dir)
            .await
            .map_err(|source| AgentWikiError::Io {
                path: index_dir.into(),
                source,
            })?;
        let lock_path = index_dir.join("sync.lock");
        let lock_target = lock_path.clone();
        let _lock = tokio::task::spawn_blocking(move || acquire_exclusive_lock(&lock_target))
            .await
            .map_err(|e| AgentWikiError::Other(format!("lock task failed: {e}")))??;
        let index = LanceIndex::open(index_dir, model.map(|_| 512)).await?;
        let prune_pending = index.has_old_versions().await?;
        Ok(Self {
            root: root.into(),
            index,
            embedding_model: model.map(|_| EMBEDDING_IDENTITY),
            embedder: OnceLock::new(),
            embedding_error: Mutex::new(None),
            lock_path,
            prune_pending,
        })
    }

    /// Load the local model on first use so unrelated use cases never pay for it.
    /// A load failure is reported as degradation and retried on the next call.
    pub(crate) async fn embedder(&self) -> Option<Arc<Mutex<Embedder>>> {
        self.embedding_model?;
        if let Some(embedder) = self.embedder.get() {
            return Some(embedder.clone());
        }
        let loaded = tokio::task::spawn_blocking(Embedder::bge_small_zh)
            .await
            .map_err(|e| format!("embedding task failed: {e}"))
            .and_then(|result| result);
        match loaded {
            Ok(embedder) => {
                let shared = Arc::new(Mutex::new(embedder));
                // Query and sync are serialized by the caller's locks, so a racing
                // loser only discards one redundant instance.
                let _ = self.embedder.set(shared);
                self.embedder.get().cloned()
            }
            Err(error) => {
                if let Ok(mut current) = self.embedding_error.lock() {
                    *current = Some(error);
                }
                None
            }
        }
    }

    fn embedding_degraded(&self, report: &mut SyncReport) {
        if let Ok(current) = self.embedding_error.lock()
            && let Some(error) = current.as_ref()
        {
            report
                .degraded
                .push(format!("embedding unavailable: {error}"));
        }
    }

    pub async fn ensure_fresh(&mut self) -> Result<SyncReport> {
        self.sync_with_vectors(false, true).await
    }

    /// Refresh document metadata without paying for semantic inference. Rule
    /// lookups need a fresh tag set, not vectors, so they use this path.
    pub async fn ensure_fresh_without_vectors(&mut self) -> Result<SyncReport> {
        self.sync_with_vectors(false, false).await
    }

    /// Hold a cross-process shared lock for the complete Lance read operation.
    pub(crate) async fn read_lock(&self) -> Result<std::fs::File> {
        let lock_path = self.lock_path.clone();
        tokio::task::spawn_blocking(move || acquire_shared_lock(&lock_path))
            .await
            .map_err(|e| AgentWikiError::Other(format!("lock task failed: {e}")))?
    }

    async fn sync_with_vectors(&mut self, rebuild: bool, embed: bool) -> Result<SyncReport> {
        let lock_path = self.lock_path.clone();
        let _lock = tokio::task::spawn_blocking(move || acquire_exclusive_lock(&lock_path))
            .await
            .map_err(|e| AgentWikiError::Other(format!("lock task failed: {e}")))??;
        self.sync_locked(rebuild, embed).await
    }

    async fn sync_locked(&mut self, rebuild: bool, embed: bool) -> Result<SyncReport> {
        let root = self.root.clone();
        let paths = tokio::task::spawn_blocking(move || document::snapshot(&root))
            .await
            .map_err(|e| AgentWikiError::Other(format!("scan task failed: {e}")))??;
        let current: BTreeSet<String> = paths.iter().map(|p| p.0.to_string()).collect();
        let previous = self.index.document_fingerprints().await?;
        let embedding_on = embed && self.embedding_model.is_some();
        let missing_vectors = if embedding_on {
            self.index.documents_missing_vectors().await?
        } else {
            Default::default()
        };
        let mut removed_by_hash: HashMap<String, Vec<String>> = HashMap::new();
        for (path, fp) in &previous {
            if !current.contains(path) {
                removed_by_hash
                    .entry(fp.content_hash.clone())
                    .or_default()
                    .push(path.clone());
            }
        }
        let mut report = SyncReport::default();
        self.embedding_degraded(&mut report);
        let mut replacements = Vec::with_capacity(WRITE_BATCH_PATHS);
        let mut replacement_rows = 0usize;
        let mut touches = Vec::with_capacity(WRITE_BATCH_PATHS);
        let mut rows_changed = false;

        for path in &paths {
            let outcome: Result<Option<PreparedReplacement>> = async {
                document::scope_path(&self.root, &path.0)?;
                let full = self.root.join(&path.0);
                let metadata =
                    tokio::fs::metadata(&full)
                        .await
                        .map_err(|source| AgentWikiError::Io {
                            path: full.clone(),
                            source,
                        })?;
                let modified = metadata.modified().map_err(|source| AgentWikiError::Io {
                    path: full.clone(),
                    source,
                })?;
                let stamp = Fingerprint {
                    content_hash: String::new(),
                    size: metadata.len(),
                    mtime_ns: modified
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_nanos() as i64,
                };
                let prev = previous.get(path.0.as_str());
                let vector_retry = embedding_on && missing_vectors.contains(path.0.as_str());
                // Skip stat-unchanged files without reading them at all.
                if prev.is_some_and(|p| p.mtime_ns == stamp.mtime_ns && p.size == stamp.size)
                    && !vector_retry
                {
                    return Ok(None);
                }
                // Retrying vectors needs the parsed document again, so re-read it.
                let previous_hash = if vector_retry {
                    None
                } else {
                    prev.map(|p| p.content_hash.clone())
                };
                let read_root = self.root.clone();
                let read_path = path.clone();
                let read = tokio::task::spawn_blocking(move || {
                    read_document_if_changed(&read_root, &read_path, previous_hash.as_deref())
                })
                .await
                .map_err(|e| AgentWikiError::Other(format!("document task failed: {e}")))?;
                let (doc, body) = match read? {
                    // Queue the stamp update so all unchanged documents share one commit.
                    DocumentRead::Unchanged(fingerprint) => {
                        touches.push((path.clone(), fingerprint));
                        return Ok(None);
                    }
                    DocumentRead::Changed(doc, body) => (doc, body),
                };
                let slices = document::chunk_document(
                    &doc.frontmatter,
                    &body,
                    path,
                    doc.fingerprint.mtime_ns,
                );
                let (edges, warnings) = relation::extract_edges(path, &doc.frontmatter, &body);
                report
                    .degraded
                    .extend(warnings.into_iter().map(|w| format!("{}: {w}", path.0)));
                let vectors = self.vectors_for(path, &slices, &mut report, embed).await?;
                let moved = prev.is_none()
                    && removed_by_hash
                        .get(&doc.fingerprint.content_hash)
                        .is_some_and(|c| c.len() == 1);
                Ok(Some(PreparedReplacement {
                    replacement: DocumentReplacement {
                        path: path.clone(),
                        slices,
                        edges,
                        vectors: vectors.vectors,
                        fingerprint: doc.fingerprint,
                        embedding_identity: self.embedding_model.map(str::to_owned),
                    },
                    moved,
                    vectors_ready: vectors.ready,
                    vectors_reused: vectors.reused,
                    vectors_pending: vectors.pending,
                }))
            }
            .await;
            match outcome {
                Ok(Some(prepared)) => {
                    let rows = prepared.replacement.slices.len() + prepared.replacement.edges.len();
                    if !replacements.is_empty()
                        && replacement_rows.saturating_add(rows) > WRITE_BATCH_ROWS
                    {
                        rows_changed |= self
                            .commit_replacements(&mut replacements, &mut report)
                            .await;
                        replacement_rows = 0;
                    }
                    replacement_rows = replacement_rows.saturating_add(rows);
                    replacements.push(prepared);
                }
                Ok(None) if !touches.last().is_some_and(|(queued, _)| queued == path) => {
                    report.unchanged += 1;
                }
                Ok(None) => {}
                Err(e) => report.degraded.push(format!(
                    "{}: {e}; projection may be stale, retry on next sync",
                    path.0
                )),
            }
            if replacements.len() == WRITE_BATCH_PATHS {
                let committed = self
                    .commit_replacements(&mut replacements, &mut report)
                    .await;
                rows_changed |= committed;
                replacement_rows = 0;
            }
            if touches.len() == WRITE_BATCH_PATHS {
                rows_changed |= self.commit_touches(&mut touches, &mut report).await;
            }
        }
        let committed = self
            .commit_replacements(&mut replacements, &mut report)
            .await;
        rows_changed |= committed;
        rows_changed |= self.commit_touches(&mut touches, &mut report).await;

        let removed = previous
            .keys()
            .filter(|path| !current.contains(*path))
            .map(|path| PathScope(path.into()))
            .collect::<Vec<_>>();
        for paths in removed.chunks(WRITE_BATCH_PATHS) {
            match self.index.delete_paths(paths).await {
                Ok(()) => {
                    report.removed += paths.len();
                    rows_changed = true;
                }
                Err(error) => {
                    for path in paths {
                        report
                            .degraded
                            .push(format!("{}: deletion failed: {error}", path.0));
                    }
                }
            }
        }
        // Repair interrupted index builds once rows exist; never fold stale rows
        // into existing indices implicitly except during an explicit rebuild.
        if rows_changed && let Err(error) = self.index.maintain_indexes(rebuild).await {
            report
                .degraded
                .push(format!("index maintenance failed: {error}"));
        }
        // Pruning is last and runs at most once while the exclusive lock is held.
        // Opening and successful writes mark cleanup pending; failures retry on
        // the next sync without making every no-op query scan the dataset.
        self.prune_pending |= rows_changed;
        if self.prune_pending {
            match self.index.prune_versions().await {
                Ok(()) => self.prune_pending = false,
                Err(error) => report
                    .degraded
                    .push(format!("version pruning failed: {error}")),
            }
        }
        report.generation = hex::encode(Sha256::digest(
            format!("{:?}", self.index.document_fingerprints().await?).as_bytes(),
        ));
        Ok(report)
    }

    async fn commit_replacements(
        &self,
        batch: &mut Vec<PreparedReplacement>,
        report: &mut SyncReport,
    ) -> bool {
        if batch.is_empty() {
            return false;
        }
        let prepared = std::mem::take(batch);
        let mut replacements = Vec::with_capacity(prepared.len());
        let mut confirmations = Vec::with_capacity(prepared.len());
        for prepared in prepared {
            replacements.push(prepared.replacement);
            confirmations.push((
                prepared.moved,
                prepared.vectors_ready,
                prepared.vectors_reused,
                prepared.vectors_pending,
            ));
        }
        match self.index.replace_documents(&replacements).await {
            Ok(()) => {
                for (moved, ready, reused, pending) in confirmations {
                    report.indexed += 1;
                    report.moved += usize::from(moved);
                    report.vectors_ready += ready;
                    report.vectors_reused += reused;
                    report.vectors_pending += pending;
                }
                true
            }
            Err(error) => {
                for replacement in replacements {
                    report.degraded.push(format!(
                        "{}: replacement failed: {error}; retry on next sync",
                        replacement.path.0
                    ));
                }
                false
            }
        }
    }

    async fn commit_touches(
        &self,
        batch: &mut Vec<(PathScope, Fingerprint)>,
        report: &mut SyncReport,
    ) -> bool {
        if batch.is_empty() {
            return false;
        }
        match self.index.update_document_fingerprints(batch).await {
            Ok(()) => {
                report.unchanged += batch.len();
                batch.clear();
                true
            }
            Err(error) => {
                for (path, _) in batch.drain(..) {
                    report.degraded.push(format!(
                        "{}: fingerprint update failed: {error}; retry on next sync",
                        path.0
                    ));
                }
                false
            }
        }
    }

    /// Reuse vectors whose exact model/dimension/input hash is already stored and
    /// recompute only the remaining ones in bounded batches.
    async fn vectors_for(
        &self,
        path: &PathScope,
        slices: &[Slice],
        report: &mut SyncReport,
        embed: bool,
    ) -> Result<VectorOutcome> {
        let Some(identity) = self.embedding_model.filter(|_| embed) else {
            return Ok(VectorOutcome {
                vectors: vec![None; slices.len()],
                ready: 0,
                reused: 0,
                pending: 0,
            });
        };
        let Some(embedder) = self.embedder().await else {
            self.embedding_degraded(report);
            return Ok(VectorOutcome {
                vectors: vec![None; slices.len()],
                ready: 0,
                reused: 0,
                pending: slices.len(),
            });
        };
        let reusable = match self.index.reusable_vectors(path).await {
            Ok(reusable) => reusable,
            Err(error) => {
                report
                    .degraded
                    .push(format!("{}: reusing vectors failed: {error}", path.0));
                HashMap::new()
            }
        };
        let mut vectors = Vec::with_capacity(slices.len());
        let mut pending = Vec::new();
        for slice in slices {
            match reusable.get(&embedding_input_hash(Some(identity), &slice.search_text)) {
                Some(vector) => vectors.push(Some(vector.clone())),
                None => {
                    vectors.push(None);
                    pending.push(slice.search_text.clone());
                }
            }
        }
        let reused = vectors.iter().filter(|v| v.is_some()).count();
        if !pending.is_empty() {
            let computed = tokio::task::spawn_blocking(move || {
                let mut embedder = embedder
                    .lock()
                    .map_err(|error| AgentWikiError::Embedding(error.to_string()))?;
                embedder
                    .embed(pending, Some(EMBED_BATCH_SIZE))
                    .map_err(AgentWikiError::Embedding)
            })
            .await
            .map_err(|e| AgentWikiError::Other(format!("embedding task failed: {e}")))?;
            match computed {
                Ok(embedded) => {
                    let mut embedded = embedded.into_iter();
                    for slot in &mut vectors {
                        if slot.is_none()
                            && let Some(vector) = embedded.next()
                        {
                            *slot = Some(vector);
                        }
                    }
                }
                Err(error) => {
                    report
                        .degraded
                        .push(format!("{}: embedding unavailable: {error}", path.0));
                    if let Ok(mut current) = self.embedding_error.lock() {
                        *current = Some(error.to_string());
                    }
                }
            }
        }
        Ok(VectorOutcome {
            ready: vectors.iter().filter(|v| v.is_some()).count(),
            reused,
            pending: vectors.iter().filter(|v| v.is_none()).count(),
            vectors,
        })
    }

    pub async fn rebuild(&mut self) -> Result<SyncReport> {
        let lock_path = self.lock_path.clone();
        let _lock = tokio::task::spawn_blocking(move || acquire_exclusive_lock(&lock_path))
            .await
            .map_err(|e| AgentWikiError::Other(format!("lock task failed: {e}")))??;
        self.index.reset().await?;
        self.prune_pending = true;
        self.sync_locked(true, true).await
    }

    /// Explicit maintenance: repair indices, fold new rows into them, then prune.
    pub async fn maintain(&mut self) -> Result<()> {
        let lock_path = self.lock_path.clone();
        let _lock = tokio::task::spawn_blocking(move || acquire_exclusive_lock(&lock_path))
            .await
            .map_err(|e| AgentWikiError::Other(format!("lock task failed: {e}")))??;
        let maintenance = self.index.maintain_indexes(true).await;
        let pruning = self.index.prune_versions().await;
        self.prune_pending = pruning.is_err();
        maintenance?;
        pruning
    }
}

fn open_lock_file(path: &Utf8Path) -> Result<std::fs::File> {
    std::fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(path)
        .map_err(|source| AgentWikiError::Io {
            path: path.into(),
            source,
        })
}

fn acquire_exclusive_lock(path: &Utf8Path) -> Result<std::fs::File> {
    let file = open_lock_file(path)?;
    FileExt::lock_exclusive(&file).map_err(|source| AgentWikiError::Io {
        path: path.into(),
        source,
    })?;
    Ok(file)
}

fn acquire_shared_lock(path: &Utf8Path) -> Result<std::fs::File> {
    let file = open_lock_file(path)?;
    FileExt::lock_shared(&file).map_err(|source| AgentWikiError::Io {
        path: path.into(),
        source,
    })?;
    Ok(file)
}
