/**
 * ESP32 Spoken Digit Classifier - TinyML Inference Wrapper
 * De tai: G1 - Dang Quoc Thanh Tai (23110149)
 * Hoc phan: Tri tue nhan tao cho IoT (261AIOT331185_01CLC)
 * 
 * Yeu cau: ESP32 (ESP-IDF >= 4.4 hoac Arduino IDE)
 *          TensorFlow Lite for Microcontrollers (TFLM)
 *          I2S Microphone (INMP441) ket noi qua GPIO
 */

#include <Arduino.h>
#include "model_data.h"

// Kich thuoc pho dau vao
#define MEL_HEIGHT 64
#define MEL_WIDTH  64
#define NUM_CLASSES 10
#define SAMPLE_RATE 8000
#define N_FFT 256
#define HOP_LENGTH 128
#define N_MELS 64

// Bo dem Tensor Arena cho TFLite Micro tren ESP32
// Kich thuoc khuyen nghi cho CNN 3 khoi: ~60 KB SRAM
constexpr int kTensorArenaSize = 60 * 1024;
uint8_t tensor_arena[kTensorArenaSize];

// I2S pins cho INMP441
#define I2S_WS  25
#define I2S_SD  33
#define I2S_SCK 32

// Buffer am thanh 1 giay = 8000 samples
int16_t audio_buffer[SAMPLE_RATE];

// Buffer dac trung log-mel 64x64
float mel_features[MEL_HEIGHT * MEL_WIDTH];

void setup() {
    Serial.begin(115200);
    while (!Serial);

    Serial.println("==================================================");
    Serial.println("ESP32 Spoken Digit Recognition");
    Serial.println("De tai G1 - Dang Quoc Thanh Tai (23110149)");
    Serial.printf("Model size in Flash: %d bytes\n", model_data_len);
    Serial.printf("Tensor Arena in SRAM: %d bytes\n", kTensorArenaSize);
    Serial.println("==================================================");

    // TODO: Khoi tao I2S cho microphone INMP441
    // i2s_config_t i2s_config = { ... };
    // i2s_pin_config_t pin_config = { ... };
    // i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    // i2s_set_pin(I2S_NUM_0, &pin_config);

    // TODO: Khoi tao TFLite Micro Interpreter
    // const tflite::Model* model = tflite::GetModel(model_data);
    // static tflite::MicroInterpreter interpreter(model, resolver, tensor_arena, kTensorArenaSize);
    // interpreter.AllocateTensors();
}

void loop() {
    Serial.println("[ESP32] Dang cho tin hieu am thanh...");
    
    // TODO: Buoc 1 - Thu am thanh 1 giay qua I2S
    // size_t bytes_read;
    // i2s_read(I2S_NUM_0, audio_buffer, sizeof(audio_buffer), &bytes_read, portMAX_DELAY);
    
    // TODO: Buoc 2 - Tien xu ly: FFT -> Mel -> log dB -> z-score
    // compute_stft(audio_buffer, SAMPLE_RATE, N_FFT, HOP_LENGTH);
    // apply_mel_filterbank(N_MELS, 0.0, 4000.0);
    // power_to_db();
    // apply_zscore(mel_features, global_mean, global_std);
    
    // TODO: Buoc 3 - Suy luan (Inference)
    // memcpy(interpreter.input(0)->data.f, mel_features, sizeof(mel_features));
    // interpreter.Invoke();
    
    // TODO: Buoc 4 - Lay argmax logits -> Chu so nhan dang (0-9)
    // float* output = interpreter.output(0)->data.f;
    // int predicted_digit = 0;
    // float max_logit = output[0];
    // for (int i = 1; i < NUM_CLASSES; i++) {
    //     if (output[i] > max_logit) { max_logit = output[i]; predicted_digit = i; }
    // }
    // Serial.printf("Nhan dang chu so: %d (logit: %.4f)\n", predicted_digit, max_logit);
    
    delay(2000);
}
