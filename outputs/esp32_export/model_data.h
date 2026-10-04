/* File tu dong sinh phuc vu nap mo hinh vao ESP32 (Flash PROGMEM) */
/* LUU Y: Day la template. De tao model_data that, can chuyen doi 
   file classifier_digits.onnx hoac .tflite sang mang byte C.
   Huong dan: xxd -i classifier_digits.tflite > model_data.h */
   
#ifndef MODEL_DATA_H
#define MODEL_DATA_H

#include <stdint.h>

// Classifier CNN 3 khoi - 21,834 tham so
// Kich thuoc mo hinh FP32: ~87.3 KB
// Kich thuoc mo hinh INT8 (luong tu hoa): ~21.8 KB 
// Thong so nay hoan toan vua voi Flash 4 MB cua ESP32

// TODO: Thay the bang mang byte thuc te sau khi chuyen doi mo hinh
// Cach tao: 
// 1. Cai dat TensorFlow: pip install tensorflow
// 2. Chuyen ONNX -> TFLite: python -c "import onnx; from onnx_tf.backend import prepare; ..."
// 3. Luong tu hoa INT8 (tuy chon)
// 4. Chuyen sang C array: xxd -i model.tflite > model_data.h

const unsigned int model_data_len = 0;  // Se duoc cap nhat khi co file thuc te
const unsigned char model_data[] = {0x00};  // Placeholder

#endif // MODEL_DATA_H
