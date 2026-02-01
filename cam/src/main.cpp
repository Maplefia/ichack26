// #include <Arduino.h>
// #include "esp_camera.h"
// #include <WiFi.h>
// #include "esp_http_server.h"
// #include "esp_heap_caps.h"

// // ====== WiFi ======
// const char* WIFI_SSID = "Not Your Wi-Fi";
// const char* WIFI_PASS = "Kerberos";

// // ====== AI Thinker ESP32-CAM pins ======
// #define PWDN_GPIO_NUM     32
// #define RESET_GPIO_NUM    -1
// #define XCLK_GPIO_NUM      0
// #define SIOD_GPIO_NUM     26
// #define SIOC_GPIO_NUM     27
// #define Y9_GPIO_NUM       35
// #define Y8_GPIO_NUM       34
// #define Y7_GPIO_NUM       39
// #define Y6_GPIO_NUM       36
// #define Y5_GPIO_NUM       21
// #define Y4_GPIO_NUM       19
// #define Y3_GPIO_NUM       18
// #define Y2_GPIO_NUM        5
// #define VSYNC_GPIO_NUM    25
// #define HREF_GPIO_NUM     23
// #define PCLK_GPIO_NUM     22

// // ====== HTTP server ======
// static httpd_handle_t camera_httpd = NULL;

// static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=frame";
// static const char* STREAM_BOUNDARY = "\r\n--frame\r\n";
// static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// // ===== Ultrasonic wiring =====
// static const int US_TRIG = 14;
// static const int US_ECHO = 15;

// // ===== Snapshot storage (captured on trigger) =====
// static uint8_t* g_snap_buf = nullptr;
// static size_t   g_snap_len = 0;
// static uint32_t g_snap_ms  = 0;

// static void free_snapshot() {
//   if (g_snap_buf) {
//     free(g_snap_buf);
//     g_snap_buf = nullptr;
//     g_snap_len = 0;
//   }
// }

// static bool store_snapshot_from_fb(const camera_fb_t* fb) {
//   if (!fb || fb->len == 0) return false;

//   // Try PSRAM first if available, else normal heap
//   free_snapshot();
//   uint8_t* buf = (uint8_t*) heap_caps_malloc(fb->len, MALLOC_CAP_SPIRAM);
//   if (!buf) buf = (uint8_t*) malloc(fb->len);
//   if (!buf) return false;

//   memcpy(buf, fb->buf, fb->len);
//   g_snap_buf = buf;
//   g_snap_len = fb->len;
//   g_snap_ms  = millis();
//   return true;
// }

// // ===== Ultrasonic functions =====
// void ultrasonicInit() {
//   pinMode(US_TRIG, OUTPUT);
//   digitalWrite(US_TRIG, LOW);
//   pinMode(US_ECHO, INPUT);
// }

// float ultrasonicReadOnceCM(uint32_t timeout_us = 30000) {
//   digitalWrite(US_TRIG, LOW);
//   delayMicroseconds(2);
//   digitalWrite(US_TRIG, HIGH);
//   delayMicroseconds(10);
//   digitalWrite(US_TRIG, LOW);

//   unsigned long duration = pulseIn(US_ECHO, HIGH, timeout_us);
//   if (duration == 0) return -1.0f;

//   float cm = duration / 58.0f;
//   if (cm < 2.0f || cm > 400.0f) return -1.0f;
//   return cm;
// }

// float ultrasonicReadMedianCM() {
//   float v[5];
//   int ok = 0;

//   for (int i = 0; i < 5; i++) {
//     float d = ultrasonicReadOnceCM();
//     if (d > 0) v[ok++] = d;
//     delay(60); // safer for HC-SR04 (prevents overlap echoes)
//   }
//   if (ok == 0) return -1.0f;

//   for (int i = 1; i < ok; i++) {
//     float key = v[i];
//     int j = i - 1;
//     while (j >= 0 && v[j] > key) { v[j + 1] = v[j]; j--; }
//     v[j + 1] = key;
//   }
//   return v[ok / 2];
// }

// // ===== Trigger state machine =====
// static float  g_baseline_cm = -1.0f;
// static int    g_stage = 0; // 0=waiting for first change, 1=waiting for reset near baseline, 2=waiting for second change
// static uint32_t g_last_check_ms = 0;
// static uint32_t g_last_capture_ms = 0;

// static const float THRESH_CM = 3.0f;       // "significant" change
// static const float RESET_CM  = 3.0f;       // must come back near baseline to arm the second trigger
// static const uint32_t DIST_PERIOD_MS = 150; // how often to sample ultrasonic
// static const uint32_t CAPTURE_COOLDOWN_MS = 2000;

// static bool should_trigger_capture(float d) {
//   if (d <= 0) return false;

//   // initialise baseline once we get a valid reading
//   if (g_baseline_cm < 0) {
//     g_baseline_cm = d;
//     g_stage = 0;
//     return false;
//   }

//   float delta = fabsf(d - g_baseline_cm);

//   // Stage 0: detect first significant change
//   if (g_stage == 0) {
//     if (delta > THRESH_CM) {
//       g_stage = 1;
//       g_baseline_cm = d;
//     }
//     return false;
//   }

//   // Stage 1: require return near baseline (debounce)
//   if (g_stage == 1) {
//     if (delta > RESET_CM) {
//       g_stage = 2;
//       g_baseline_cm = d;
//     }
//     return false;
//   }

//   // Stage 2: detect second significant change -> trigger capture
//   if (g_stage == 2) {
//     if (delta > THRESH_CM) {
//       g_stage = 0; // reset for next cycle
//       // optional: refresh baseline after a capture cycle
//       g_baseline_cm = d;
//       return true;
//     }
//   }

//   return false;
// }

// // ===== HTTP handlers =====
// static esp_err_t index_handler(httpd_req_t *req) {
//   const char html[] =
//     "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
//     "<title>ESP32-CAM</title></head><body style='margin:0; font-family:sans-serif;'>"
//     "<h3 style='padding:12px;'>ESP32-CAM Live Stream</h3>"
//     "<img src='/stream' style='width:100%; max-width:720px; height:auto; display:block; padding:12px;'/>"
//     "<p style='padding:12px;'>Triggered snapshot: <a href='/capture'>/capture</a></p>"
//     "</body></html>";
//   httpd_resp_set_type(req, "text/html");
//   return httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
// }

// // /capture now returns the *last triggered snapshot* if available,
// // otherwise it captures a fresh frame.
// static esp_err_t capture_handler(httpd_req_t *req) {
//   if (g_snap_buf && g_snap_len > 0) {
//     httpd_resp_set_type(req, "image/jpeg");
//     httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=triggered.jpg");
//     return httpd_resp_send(req, (const char*)g_snap_buf, g_snap_len);
//   }

//   camera_fb_t *fb = esp_camera_fb_get();
//   if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }

//   httpd_resp_set_type(req, "image/jpeg");
//   httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
//   esp_err_t res = httpd_resp_send(req, (const char*)fb->buf, fb->len);
//   esp_camera_fb_return(fb);
//   return res;
// }

// static esp_err_t stream_handler(httpd_req_t *req) {
//   httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
//   httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

//   while (true) {
//     // Rate-limit ultrasonic checks
//     uint32_t now = millis();
//     if (now - g_last_check_ms > DIST_PERIOD_MS) {
//       g_last_check_ms = now;
//       float d = ultrasonicReadMedianCM();
//       if (d > 0) {
//         Serial.printf("Dist: %.1f cm (baseline=%.1f stage=%d)\n", d, g_baseline_cm, g_stage);

//         if ((now - g_last_capture_ms) > CAPTURE_COOLDOWN_MS && should_trigger_capture(d)) {
//           // Capture *right now* from the live loop
//           camera_fb_t *snap = esp_camera_fb_get();
//           if (snap) {
//             if (store_snapshot_from_fb(snap)) {
//               g_last_capture_ms = now;
//               Serial.printf("Triggered SNAP saved: %u bytes at %u ms\n", (unsigned)g_snap_len, (unsigned)g_snap_ms);
//             } else {
//               Serial.println("Failed to allocate snapshot buffer");
//             }
//             esp_camera_fb_return(snap);
//           } else {
//             Serial.println("Snapshot capture failed (fb null)");
//           }
//         }
//       }
//     }

//     // Stream one frame
//     camera_fb_t *fb = esp_camera_fb_get();
//     if (!fb) {
//       Serial.println("Camera capture failed");
//       continue;
//     }

//     if (httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY)) != ESP_OK) {
//       esp_camera_fb_return(fb);
//       break;
//     }

//     char part_buf[64];
//     int hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART, (unsigned)fb->len);
//     if (httpd_resp_send_chunk(req, part_buf, hlen) != ESP_OK) {
//       esp_camera_fb_return(fb);
//       break;
//     }

//     if (httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len) != ESP_OK) {
//       esp_camera_fb_return(fb);
//       break;
//     }

//     esp_camera_fb_return(fb);
//     vTaskDelay(1);
//   }

//   httpd_resp_send_chunk(req, NULL, 0);
//   return ESP_OK;
// }

// // ===== Camera + server init =====
// static void startCameraServer() {
//   httpd_config_t config = HTTPD_DEFAULT_CONFIG();
//   config.server_port = 80;

//   httpd_uri_t index_uri  = { .uri="/",        .method=HTTP_GET, .handler=index_handler,   .user_ctx=NULL };
//   httpd_uri_t cap_uri    = { .uri="/capture", .method=HTTP_GET, .handler=capture_handler, .user_ctx=NULL };
//   httpd_uri_t stream_uri = { .uri="/stream",  .method=HTTP_GET, .handler=stream_handler,  .user_ctx=NULL };

//   if (httpd_start(&camera_httpd, &config) == ESP_OK) {
//     httpd_register_uri_handler(camera_httpd, &index_uri);
//     httpd_register_uri_handler(camera_httpd, &cap_uri);
//     httpd_register_uri_handler(camera_httpd, &stream_uri);
//   }
// }

// static void initCamera() {
//   camera_config_t config;
//   config.ledc_channel = LEDC_CHANNEL_0;
//   config.ledc_timer   = LEDC_TIMER_0;
//   config.pin_d0       = Y2_GPIO_NUM;
//   config.pin_d1       = Y3_GPIO_NUM;
//   config.pin_d2       = Y4_GPIO_NUM;
//   config.pin_d3       = Y5_GPIO_NUM;
//   config.pin_d4       = Y6_GPIO_NUM;
//   config.pin_d5       = Y7_GPIO_NUM;
//   config.pin_d6       = Y8_GPIO_NUM;
//   config.pin_d7       = Y9_GPIO_NUM;
//   config.pin_xclk     = XCLK_GPIO_NUM;
//   config.pin_pclk     = PCLK_GPIO_NUM;
//   config.pin_vsync    = VSYNC_GPIO_NUM;
//   config.pin_href     = HREF_GPIO_NUM;
//   config.pin_sccb_sda = SIOD_GPIO_NUM;
//   config.pin_sccb_scl = SIOC_GPIO_NUM;
//   config.pin_pwdn     = PWDN_GPIO_NUM;
//   config.pin_reset    = RESET_GPIO_NUM;

//   config.xclk_freq_hz = 20000000;
//   config.pixel_format = PIXFORMAT_JPEG;
//   config.frame_size   = FRAMESIZE_VGA;
//   config.jpeg_quality = 12;
//   config.fb_count     = 2;
//   config.grab_mode    = CAMERA_GRAB_LATEST;

//   esp_err_t err = esp_camera_init(&config);
//   if (err != ESP_OK) {
//     Serial.printf("Camera init failed: 0x%x\n", err);
//     ESP.restart();
//   }
//   Serial.println("Camera init OK");
// }

// static void wifiConnectSimple() {
//   WiFi.mode(WIFI_STA);
//   WiFi.setSleep(false);
//   WiFi.begin(WIFI_SSID, WIFI_PASS);

//   Serial.print("WiFi connecting");
//   while (WiFi.status() != WL_CONNECTED) {
//     delay(250);
//     Serial.print(".");
//   }
//   Serial.println();
//   Serial.print("IP: ");
//   Serial.println(WiFi.localIP());
// }

// void setup() {
//   Serial.begin(115200);
//   delay(300);

//   ultrasonicInit();      // <-- YOU WERE MISSING THIS
//   initCamera();
//   wifiConnectSimple();   // <-- connect ONCE (no double begin)

//   startCameraServer();
//   Serial.println("Open http://<IP>/ or http://<IP>/stream");
// }

// void loop() {
//   delay(1000);
// }


#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include "esp_heap_caps.h"
#include <HTTPClient.h>
#include "esp_task_wdt.h"

// ====== WiFi ======
const char* WIFI_SSID = "Not Your Wi-Fi";
const char* WIFI_PASS = "Kerberos";

// const char* WIFI_SSID = "Ari";
// const char* WIFI_PASS = "poogy1402";


// ====== Backend (Flask) ======
// Put your friend's machine IP here (the one printed by Flask, e.g. 172.20.10.x on hotspot)
const char* BACKEND_HOST = "10.156.119.160";
const int   BACKEND_PORT = 5001;

// Upload endpoints on backend:
static String backendUrl(const char* path) {
  return String("http://") + BACKEND_HOST + ":" + String(BACKEND_PORT) + String(path);
}
static String botId() {
  return WiFi.macAddress();  // e.g. "A4:CF:12:34:56:78"
}

// ====== AI Thinker ESP32-CAM pins ======
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ====== HTTP server ======
static httpd_handle_t camera_httpd = NULL;

static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=frame";
static const char* STREAM_BOUNDARY = "\r\n--frame\r\n";
static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// ===== Ultrasonic wiring =====
static const int US_TRIG = 14;
static const int US_ECHO = 15;

// ===== Snapshot storage (captured on trigger) =====
static uint8_t* g_snap_buf = nullptr;
static size_t   g_snap_len = 0;
static uint32_t g_snap_ms  = 0;


// ===== Flash LED (AI Thinker usually GPIO4) =====
#define LED_GPIO_NUM 4
static uint32_t g_last_led_ms = 0;
static bool g_led_on = false;
#define LED_GPIO_NUM 4

// PWM settings
static const int LEDC_CH = 7;          // any free channel 0-15
static const int LEDC_FREQ = 5000;     // 5 kHz
static const int LEDC_RES_BITS = 8;    // 0..255 duty
static const int LED_MAX = 255;

// 0 = off, 255 = full bright
static void ledSetBrightness(uint8_t duty) {
  ledcWrite(LEDC_CH, duty);
}

static void ledInitPWM() {
  ledcSetup(LEDC_CH, LEDC_FREQ, LEDC_RES_BITS);
  ledcAttachPin(LED_GPIO_NUM, LEDC_CH);
  ledSetBrightness(0);
}


static void ledUpdateForStage(int stage) {
  const uint8_t DIM = 20;  // <<< change this (0..255). Start at 10–30.
  const uint32_t PERIOD = 400;

  if (stage == 1) {
    g_led_on = false;
    ledSetBrightness(0);
    return;
  }

  uint32_t now = millis();
  if (now - g_last_led_ms >= PERIOD) {
    g_last_led_ms = now;
    g_led_on = !g_led_on;
    ledSetBrightness(g_led_on ? DIM : 0);
  }
}


static void free_snapshot() {
  if (g_snap_buf) {
    free(g_snap_buf);
    g_snap_buf = nullptr;
    g_snap_len = 0;
  }
}

static bool store_snapshot_from_fb(const camera_fb_t* fb) {
  if (!fb || fb->len == 0) return false;

  free_snapshot();

  // Try PSRAM first if available, else normal heap
  uint8_t* buf = (uint8_t*) heap_caps_malloc(fb->len, MALLOC_CAP_SPIRAM);
  if (!buf) buf = (uint8_t*) malloc(fb->len);
  if (!buf) return false;

  memcpy(buf, fb->buf, fb->len);
  g_snap_buf = buf;
  g_snap_len = fb->len;
  g_snap_ms  = millis();
  return true;
}

// ===== Ultrasonic functions =====
void ultrasonicInit() {
  pinMode(US_TRIG, OUTPUT);
  digitalWrite(US_TRIG, LOW);
  pinMode(US_ECHO, INPUT);
}

float ultrasonicReadOnceCM(uint32_t timeout_us = 30000) {
  digitalWrite(US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(US_TRIG, LOW);

  unsigned long duration = pulseIn(US_ECHO, HIGH, timeout_us);
  if (duration == 0) return -1.0f;

  float cm = duration / 58.0f;
  if (cm < 2.0f || cm > 400.0f) return -1.0f;
  return cm;
}

float ultrasonicReadMedianCM() {
  float v[5];
  int ok = 0;

  for (int i = 0; i < 5; i++) {
    float d = ultrasonicReadOnceCM();
    if (d > 0) v[ok++] = d;
    delay(60);
  }
  if (ok == 0) return -1.0f;

  for (int i = 1; i < ok; i++) {
    float key = v[i];
    int j = i - 1;
    while (j >= 0 && v[j] > key) { v[j + 1] = v[j]; j--; }
    v[j + 1] = key;
  }
  return v[ok / 2];
}

// ===== Trigger state machine =====
// Interpretation: deviate (event1) -> deviate again (event2) triggers capture.
// (If you wanted deviate->return->deviate, tell me and I'll switch it.)
static float   g_baseline_cm = -1.0f;
static int     g_stage = 0; // 0 waiting for event1, 1 waiting for event2
static uint32_t g_last_check_ms = 0;
static uint32_t g_last_capture_ms = 0;

static const float THRESH_CM = 1.5f;
static const uint32_t DIST_PERIOD_MS = 150;
static const uint32_t CAPTURE_COOLDOWN_MS = 2000;

// ===== Frame push controls =====
static uint32_t g_last_frame_push_ms = 0;
static const uint32_t FRAME_PUSH_PERIOD_MS = 800; // ~1.25 fps to backend
static const uint32_t HTTP_TIMEOUT_MS = 2500;

// ===== HTTP posting (raw JPEG) =====
static bool postJpegToBackend(const char* path, const uint8_t* data, size_t len) {
  if (!data || len == 0) return false;
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);

  String url = backendUrl(path);
  http.begin(url);
  http.addHeader("Content-Type", "image/jpeg");

  // HTTPClient POST expects uint8_t* (non-const) in this core
  int code = http.POST((uint8_t*)data, len);

  http.end();

  Serial.printf("POST %s -> HTTP %d (len=%u)\n", path, code, (unsigned)len);
  return (code >= 200 && code < 300);
}

static bool should_trigger_capture(float d) {
  if (d <= 0) return false;

  if (g_baseline_cm < 0) {
    g_baseline_cm = d;
    g_stage = 0;
    return true;
  }


  float delta = fabsf(d - g_baseline_cm);

  // Event 1: first significant change
  if (g_stage == 0) {
    if (delta > THRESH_CM) {
      g_stage = 1;
      g_baseline_cm = d; // update baseline to new state (so second change is relative)
      return false;
    }
    return false;
  }

  // Event 2: second significant change
  if (g_stage == 1) {
    if (delta > THRESH_CM) {
      
      g_stage = 2;
      g_baseline_cm = d;
      return true;
    }
  }

  if (g_stage == 2) {
    if (delta > THRESH_CM) {
      g_stage = 0;
      g_baseline_cm = d; // update baseline to new state (so second change is relative)
      return true;
    }
    return false;
  }

  return false;
}

// ===== HTTP handlers =====
static esp_err_t index_handler(httpd_req_t *req) {
  const char html[] =
    "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>ESP32-CAM</title></head><body style='margin:0; font-family:sans-serif;'>"
    "<h3 style='padding:12px;'>ESP32-CAM Live Stream</h3>"
    "<img src='/stream' style='width:100%; max-width:720px; height:auto; display:block; padding:12px;'/>"
    "<p style='padding:12px;'>Triggered snapshot: <a href='/capture'>/capture</a></p>"
    "</body></html>";
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
}

// /capture returns last triggered snapshot if available, otherwise fresh
static esp_err_t capture_handler(httpd_req_t *req) {
  if (g_snap_buf && g_snap_len > 0) {
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=triggered.jpg");
    return httpd_resp_send(req, (const char*)g_snap_buf, g_snap_len);
  }

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  esp_err_t res = httpd_resp_send(req, (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

static esp_err_t stream_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    ledUpdateForStage(g_stage);

    uint32_t now = millis();
    int counter = 0;

    // ---- Ultrasonic trigger check (rate-limited) ----
    if (now - g_last_check_ms > DIST_PERIOD_MS) {
      g_last_check_ms = now;
      float d = ultrasonicReadMedianCM();

      if (d) {
        
        Serial.printf("Dist: %.1f cm (baseline=%.1f stage=%d)\n", d, g_baseline_cm, g_stage);

        if ((now - g_last_capture_ms) > CAPTURE_COOLDOWN_MS && should_trigger_capture(d)) {
          delay(3000); // small delay to allow scene to stabilise
          if (counter == 0){
          camera_fb_t *snap = esp_camera_fb_get();
          if (snap) {
            bool stored = store_snapshot_from_fb(snap);
            if (stored) {
              g_last_capture_ms = now;
              Serial.printf("Triggered SNAP saved: %u bytes\n", (unsigned)g_snap_len);

              // Push triggered capture to backend
              postJpegToBackend("/api/capture", snap->buf, snap->len);
            } else {
              Serial.println("Failed to allocate snapshot buffer");
            }
            esp_camera_fb_return(snap);
          } else {
            Serial.println("Snapshot capture failed (fb null)");
          }
          counter = 1;
          }
          else{
            counter = 0;
          }
        }
      }
    }

    // ---- Stream one frame ----
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      continue;
    }

    // Optional: push low-FPS frames to backend as "live"
    if (now - g_last_frame_push_ms > FRAME_PUSH_PERIOD_MS) {
      g_last_frame_push_ms = now;
      postJpegToBackend("/api/frame", fb->buf, fb->len);
    }



    if (httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY)) != ESP_OK) {
      esp_camera_fb_return(fb);
      break;
    }

    char part_buf[64];
    int hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART, (unsigned)fb->len);
    if (httpd_resp_send_chunk(req, part_buf, hlen) != ESP_OK) {
      esp_camera_fb_return(fb);
      break;
    }

    if (httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len) != ESP_OK) {
      esp_camera_fb_return(fb);
      break;
    }

    esp_camera_fb_return(fb);
    vTaskDelay(1);
  }

  httpd_resp_send_chunk(req, NULL, 0);
  return ESP_OK;
}

// ===== Camera + server init =====
static void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  httpd_uri_t index_uri  = { .uri="/",        .method=HTTP_GET, .handler=index_handler,   .user_ctx=NULL };
  httpd_uri_t cap_uri    = { .uri="/capture", .method=HTTP_GET, .handler=capture_handler, .user_ctx=NULL };
  httpd_uri_t stream_uri = { .uri="/stream",  .method=HTTP_GET, .handler=stream_handler,  .user_ctx=NULL };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &cap_uri);
    httpd_register_uri_handler(camera_httpd, &stream_uri);
  }
}

static void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Keep this moderate; too large + HTTP posts = pain
  config.frame_size   = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count     = 2;
  config.grab_mode    = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    ESP.restart();
  }
  Serial.println("Camera init OK");
}

static void wifiConnectSimple() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

static bool postBotStatus(const char* status, float battery01) {
  if (WiFi.status() != WL_CONNECTED) return false;

  // battery as string like "0.60"
  char batt[16];
  snprintf(batt, sizeof(batt), "%.2f", battery01);

  String body = String("{\"id\":\"") + botId() +
                String("\",\"status\":\"") + status +
                String("\",\"battery\":\"") + batt + String("\"}");

  HTTPClient http;
  http.setTimeout(2000);
  http.begin(backendUrl("/api/bots"));
  http.addHeader("Content-Type", "application/json");

  int code = http.POST((uint8_t*)body.c_str(), body.length());
  http.end();

  Serial.printf("POST /api/bots -> %d | %s\n", code, body.c_str());
  return (code >= 200 && code < 300);
}



void setup() {
  Serial.begin(115200);
  delay(300);

  ultrasonicInit();
  ledInitPWM();
  initCamera();
  wifiConnectSimple();

  Serial.printf("Backend capture URL: %s\n", backendUrl("/api/capture").c_str());
  Serial.printf("Backend frame URL:   %s\n", backendUrl("/api/frame").c_str());

  startCameraServer();
  Serial.println("Open http://<ESP_IP>/ or http://<ESP_IP>/stream");
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last > 3000) { // every 3s
    last = millis();

    // TODO: replace with real battery reading if you have one
    float fakeBattery = (1.0f - (float)(millis() % 600000) / 600000.0f)*100; // drains over 10min

    postBotStatus("Connected", fakeBattery);
  }

  delay(10);
}
