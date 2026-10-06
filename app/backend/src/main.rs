use std::net::SocketAddr;

use tracing_subscriber::EnvFilter;

mod db;
mod models;
mod routes;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("backend=info".parse().unwrap()))
        .init();

    let state = db::AppState::new("data/music_color.lbdb").expect("failed to initialize LadybugDB");

    let count = state
        .seed_from_manifest("data/manifest/tracks.jsonl")
        .expect("failed to seed manifest");
    tracing::info!("seeded {count} tracks from manifest");

    let app = routes::build(state);

    let addr = SocketAddr::from(([127, 0, 0, 1], 3001));
    tracing::info!("listening on http://{addr}");

    let listener = tokio::net::TcpListener::bind(addr).await.expect("failed to bind");
    axum::serve(listener, app).await.expect("server error");
}
