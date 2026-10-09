use std::net::SocketAddr;

use tracing_subscriber::EnvFilter;

mod db;
mod models;
mod routes;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::from_default_env().add_directive("backend=info".parse().unwrap()),
        )
        .init();

    let lbdb_path = env_or("LBDB_PATH", "data/music_color.lbdb");
    let manifest_path = env_or("MANIFEST_PATH", "data/manifest/tracks.jsonl");

    let state = db::AppState::new(&lbdb_path).expect("failed to initialize LadybugDB");

    let count = state
        .seed_from_manifest(&manifest_path)
        .expect("failed to seed manifest");
    tracing::info!("seeded {count} tracks from manifest");

    let app = routes::build(state);

    let port: u16 = env_or("PORT", "3001").parse().unwrap_or(3001);
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("listening on http://{addr}");

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind");
    axum::serve(listener, app).await.expect("server error");
}

fn env_or(name: &str, fallback: &str) -> String {
    std::env::var(name).unwrap_or_else(|_| fallback.to_string())
}
