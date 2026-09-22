//! FastEmbed adapter boundary.
//!
//! Model construction lives here; retrieval and synchronization must not
//! import FastEmbed types directly.

use fastembed::{Embedding, EmbeddingModel, TextEmbedding, TextInitOptions};
use std::path::PathBuf;

/// Local embedding adapter backed by FastEmbed's ONNX runtime.
pub struct Embedder(TextEmbedding);

impl Embedder {
    /// Load the first supported Chinese model. Model files are cached locally.
    pub fn bge_small_zh() -> Result<Self, String> {
        let cache_dir = dirs::home_dir()
            .map(|path| path.join(".agentwiki/cache/fastembed"))
            .unwrap_or_else(|| PathBuf::from(".agentwiki/cache/fastembed"));
        let options = TextInitOptions::new(EmbeddingModel::BGESmallZHV15)
            .with_cache_dir(cache_dir)
            .with_show_download_progress(true);
        TextEmbedding::try_new(options)
            .map(Self)
            .map_err(|e| e.to_string())
    }

    /// Embed prepared chunk or query inputs, letting FastEmbed batch internally.
    pub fn embed(
        &mut self,
        inputs: Vec<String>,
        batch_size: Option<usize>,
    ) -> Result<Vec<Embedding>, String> {
        self.0.embed(inputs, batch_size).map_err(|e| e.to_string())
    }
}
