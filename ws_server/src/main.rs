use actix_cors::Cors;
use actix_web::{
    App, Error, HttpRequest, HttpResponse, HttpServer, Responder, post, rt, web, web::Payload,
};
use actix_ws::AggregatedMessage;
use futures_util::StreamExt as _;
use std::{collections::HashMap, env};
use tokio::{
    select,
    sync::{RwLock, broadcast},
};

// 统一响应结构体
#[derive(serde::Serialize)]
struct ApiResponse<T> {
    code: i32,
    success: bool,
    msg: String,
    data: Option<T>,
}

impl<T> ApiResponse<T> {
    // 添加一个专门用于无数据响应的静态方法
    fn success_without_data(msg: String) -> ApiResponse<()> {
        ApiResponse {
            code: 200,
            success: true,
            msg,
            data: None,
        }
    }

    fn error(code: i32, msg: String) -> ApiResponse<()> {
        ApiResponse {
            code,
            success: false,
            msg,
            data: None,
        }
    }
}
// 定义消息类型（可以根据需求扩展为结构体）
type WsMessage = String;
#[derive(Clone)]
struct AppState {
    // 使用 HashMap 存储不同 user_signature 的广播通道
    tx_map: web::Data<RwLock<HashMap<String, broadcast::Sender<WsMessage>>>>,
    api_token: Option<String>,
}

fn _error_response(code: i32, msg: &str) -> HttpResponse {
    HttpResponse::BadRequest().json(ApiResponse::<()>::error(code, msg.to_string()))
}

fn _unauthorized_response(msg: &str) -> HttpResponse {
    HttpResponse::Unauthorized().json(ApiResponse::<()>::error(401, msg.to_string()))
}

fn _query_param(req: &HttpRequest, key: &str) -> Option<String> {
    req.query_string().split('&').find_map(|pair| {
        let mut parts = pair.splitn(2, '=');
        match (parts.next(), parts.next()) {
            (Some(k), Some(v)) if k == key => Some(v.to_string()),
            _ => None,
        }
    })
}

fn _is_valid_user_signature(signature: &str) -> bool {
    let length = signature.len();
    if !(8..=128).contains(&length) {
        return false;
    }
    signature
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || ch == '-' || ch == '_')
}

fn _extract_user_signature_from_header(req: &HttpRequest) -> Result<String, HttpResponse> {
    let signature = req
        .headers()
        .get("userSignature")
        .and_then(|value| value.to_str().ok())
        .map(str::trim)
        .ok_or_else(|| _error_response(400, "缺少 userSignature 请求头"))?;

    if !_is_valid_user_signature(signature) {
        return Err(_error_response(400, "userSignature 格式不合法"));
    }
    Ok(signature.to_string())
}

fn _extract_user_signature_from_query(req: &HttpRequest) -> Result<String, HttpResponse> {
    let signature = _query_param(req, "userSignature")
        .map(|item| item.trim().to_string())
        .ok_or_else(|| _error_response(400, "缺少 userSignature 查询参数"))?;

    if !_is_valid_user_signature(&signature) {
        return Err(_error_response(400, "userSignature 格式不合法"));
    }
    Ok(signature)
}

fn _assert_api_token(req: &HttpRequest, expected_token: Option<&str>) -> Result<(), HttpResponse> {
    let Some(expected) = expected_token else {
        return Ok(());
    };
    let incoming = req
        .headers()
        .get("x-ws-token")
        .and_then(|value| value.to_str().ok())
        .map(str::trim);
    if incoming == Some(expected) {
        return Ok(());
    }
    Err(_unauthorized_response("x-ws-token 鉴权失败"))
}

fn _assert_ws_query_token(req: &HttpRequest, expected_token: Option<&str>) -> Result<(), HttpResponse> {
    let Some(expected) = expected_token else {
        return Ok(());
    };
    let incoming = _query_param(req, "token");
    if incoming.as_deref() == Some(expected) {
        return Ok(());
    }
    Err(_unauthorized_response("WebSocket token 鉴权失败"))
}

fn _resolve_allowed_origins() -> Vec<String> {
    let from_env = env::var("WS_ALLOWED_ORIGINS")
        .ok()
        .map(|raw| {
            raw.split(',')
                .map(str::trim)
                .filter(|item| !item.is_empty())
                .map(str::to_string)
                .collect::<Vec<String>>()
        })
        .unwrap_or_default();
    if !from_env.is_empty() {
        return from_env;
    }
    vec![
        "http://127.0.0.1:6719".to_string(),
        "http://localhost:6719".to_string(),
        "http://127.0.0.1:8000".to_string(),
        "http://localhost:8000".to_string(),
    ]
}

fn _resolve_api_token() -> Option<String> {
    env::var("WS_API_TOKEN")
        .ok()
        .map(|token| token.trim().to_string())
        .filter(|token| !token.is_empty())
}

#[post("/user-msg")]
async fn user_msg(req: HttpRequest, req_body: String, data: web::Data<AppState>) -> impl Responder {
    if let Err(resp) = _assert_api_token(&req, data.api_token.as_deref()) {
        return resp;
    }
    let target_user_signature = match _extract_user_signature_from_header(&req) {
        Ok(value) => value,
        Err(resp) => return resp,
    };
    // 打印接收到的消息
    println!("Received /user-msg: {}", req_body);
    // 获取对应 user_signature 的发送端
    let tx_map = data.tx_map.read().await;
    if let Some(tx) = tx_map.get(&target_user_signature) {
        match tx.send(req_body.clone()) {
            Ok(_) => HttpResponse::Ok().json(ApiResponse::<()>::success_without_data(
                "发送成功".to_string(),
            )),
            Err(e) => {
                eprintln!("Failed to send message: {}", e);
                HttpResponse::InternalServerError()
                    .json(ApiResponse::<()>::error(500, "系统服务异常".to_string()))
            }
        }
    } else {
        HttpResponse::NotFound().json(ApiResponse::<()>::error(
            404,
            "后台服务未启动，请联系管理员".to_string(),
        ))
    }
}

async fn echo(
    req: HttpRequest,
    stream: Payload,
    data: web::Data<AppState>,
) -> Result<HttpResponse, Error> {
    if let Err(resp) = _assert_ws_query_token(&req, data.api_token.as_deref()) {
        return Ok(resp);
    }
    let user_signature = match _extract_user_signature_from_query(&req) {
        Ok(value) => value,
        Err(resp) => return Ok(resp),
    };

    let (res, mut session, stream) = actix_ws::handle(&req, stream)?;
    println!("New WebSocket connection:{:?}", req.query_string());
    println!("user_signature: {}", user_signature);

    // 订阅广播通道（每个连接创建独立的接收端）
    // 为当前 user_signature 创建或获取广播通道
    let tx = {
        let mut tx_map = data.tx_map.write().await;
        if !tx_map.contains_key(&user_signature) {
            // 为这个 user_signature 创建新的广播通道
            let (new_tx, _) = broadcast::channel::<WsMessage>(1024);
            tx_map.insert(user_signature.clone(), new_tx.clone());
            new_tx
        } else {
            tx_map
                .get(&user_signature)
                .expect("user_signature exists in tx_map")
                .clone()
        }
    };

    let mut rx = tx.subscribe();
    let mut stream = stream
        .aggregate_continuations()
        .max_continuation_size(2_usize.pow(20));

    // 启动异步任务处理 WebSocket 消息和广播消息
    rt::spawn(async move {
        // 同时监听：1. WebSocket 客户端消息 2. 广播通道消息
        loop {
            select! {
                // 监听来自客户端的 WebSocket 消息（原 echo 逻辑）
                msg = stream.next() => {
                    match msg {
                        Some(Ok(AggregatedMessage::Text(text))) => {
                            println!("WebSocket client sent: {}", text);
                            // 回声（可选：保留原 echo 功能）
                            // 如果是ping消息则不回声
                            if text != "ping" {
                                // 回声
                                if let Err(e) = session.text(text.clone()).await {
                                    eprintln!("Failed to send text: {}", e);
                                    break;
                                }
                            }
                        }
                        Some(Ok(AggregatedMessage::Binary(bin))) => {
                            println!("WebSocket client sent binary: {:?}", bin);
                            if let Err(e) = session.binary(bin).await {
                                eprintln!("Failed to send binary: {}", e);
                                break;
                            }
                        }
                        Some(Ok(AggregatedMessage::Ping(msg))) => {
                            println!("WebSocket client sent ping: {:?}", msg);
                            // if let Err(e) = session.pong(&msg).await {
                            //     eprintln!("Failed to send pong: {}", e);
                            //     break;
                            // }
                        }
                        // 客户端断开连接或出错，退出循环
                        None | Some(Err(_)) => {
                            println!("WebSocket connection closed");
                            break;
                        }
                        _ => {}
                    }
                }
                // 监听广播通道的消息（来自 /user-msg）
                msg = rx.recv() => {
                    match msg {
                        Ok(text) => {
                            // 将广播消息发送给 WebSocket 客户端
                            if let Err(e) = session.text(text).await {
                                eprintln!("Failed to send broadcast msg: {}", e);
                                break;
                            }
                        }
                        Err(broadcast::error::RecvError::Closed) => {
                            eprintln!("Broadcast channel closed");
                            break;
                        }
                        Err(broadcast::error::RecvError::Lagged(_)) => {
                            eprintln!("Broadcast message lagged, missed some messages");
                        }
                    }
                }
            }
        }

        // 关闭 WebSocket 连接
        let _ = session.close(None).await;
    });

    Ok(res)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let tx_map = web::Data::new(RwLock::new(HashMap::new()));
    let allowed_origins = _resolve_allowed_origins();
    let app_state = AppState {
        tx_map,
        api_token: _resolve_api_token(),
    };

    HttpServer::new(move || {
        let mut cors = Cors::default()
            .allow_any_method()
            .allow_any_header()
            .supports_credentials();
        for origin in &allowed_origins {
            cors = cors.allowed_origin(origin);
        }
        App::new()
            // 注入应用状态（广播通道发送端）
            .app_data(web::Data::new(app_state.clone()))
            // 跨域配置（生产环境需限制 origin）
            .wrap(cors)
            .service(web::scope("/api").service(user_msg))
            .route("/echo", web::get().to(echo))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
