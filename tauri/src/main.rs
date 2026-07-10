#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Start Python backend
            let app_handle = app.handle();
            tauri::async_runtime::spawn(async move {
                let backend_path = std::env::current_exe()
                    .unwrap()
                    .parent()
                    .unwrap()
                    .join("backend");

                let python_path = if cfg!(target_os = "windows") {
                    backend_path.join("python.exe")
                } else {
                    backend_path.join("bin").join("python")
                };

                let _ = tokio::process::Command::new(python_path)
                    .arg("-m")
                    .arg("uvicorn")
                    .arg("app.main:app")
                    .arg("--host")
                    .arg("127.0.0.1")
                    .arg("--port")
                    .arg("8000")
                    .current_dir(&backend_path)
                    .spawn();
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
