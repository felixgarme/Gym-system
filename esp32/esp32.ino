#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include "Animaciones.h"

#define TFT_CS   7
#define TFT_DC   1
#define TFT_RST  0
#define TFT_SDA  5
#define TFT_SCL  4

Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);

unsigned long ultimoMensaje = 0;
const unsigned long TIEMPO_DESCONEXION = 3000;
bool bsodMostrado = false;

unsigned long ultimoIntentoBusqueda = 0;
const unsigned long INTERVALO_BUSQUEDA = 500; 

// Buffer para 1 línea de 240 píxeles (cada píxel RGB565 usa 2 bytes = 480 bytes total)
uint16_t bufferLinea[240];

void recibirImagen() {
  apagarFaceID(); 
  
  // Limpiamos la pantalla a negro puro para que la imagen se dibuje sobre un lienzo limpio
  tft.fillScreen(ST77XX_BLACK);
  
  // Limpiamos cualquier basura en el puerto serial antes de empezar
  while(Serial.available()) Serial.read();
  
  // Avisamos a Python que estamos listos para recibir los datos
  Serial.println("READY");

  // Recepción ultra rápida por bloques (línea por línea)
  for(int y = 0; y < 240; y++) {
    // Leemos exactamente 480 bytes (240 píxeles * 2 bytes)
    size_t leidos = Serial.readBytes((uint8_t*)bufferLinea, 480);
    
    // Si no llegaron los 480 bytes en el tiempo esperado (timeout), abortamos y limpiamos
    if (leidos < 480) {
      while(Serial.available()) Serial.read(); 
      return; 
    }
    
    // Dibujamos la línea en la pantalla inmediatamente
    tft.drawRGBBitmap(0, y, bufferLinea, 240, 1);
    
    // ¡CRÍTICO! Alimenta el Watchdog Timer del ESP32 para evitar que 
    // se reinicie por "pensar" demasiado tiempo durante la recepción.
    yield(); 
  }
  
  ultimoMensaje = millis();
  bsodMostrado = false;
}

void setup() {
  Serial.setRxBufferSize(4096); 
  Serial.begin(921600);
  
  // Establece un timeout de 1000ms. Si readBytes no recibe los datos a tiempo, se cancela.
  Serial.setTimeout(1000);
  
  SPI.begin(TFT_SCL, -1, TFT_SDA, TFT_CS);
  tft.init(240, 240);
  tft.setSPISpeed(40000000);
  tft.setRotation(3); 
  
  mostrarBSOD(tft);
  bsodMostrado = true;
  ultimoIntentoBusqueda = millis();
}

void loop() {
  // Manejo de la Desconexión
  if (millis() - ultimoMensaje > TIEMPO_DESCONEXION) {
    if (!bsodMostrado) {
      mostrarBSOD(tft);
      bsodMostrado = true;
      ultimoIntentoBusqueda = millis();
    } else {
      if (millis() - ultimoIntentoBusqueda > INTERVALO_BUSQUEDA) {
        ultimoIntentoBusqueda = millis();
        Serial.println("ESP32_BEACON"); 
      }
    }
  }

  // Mantiene vivo el parpadeo y efectos de la pantalla
  animarFaceID(tft);

  // Escucha de comandos desde Python
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    if (comando == "PING") {
      ultimoMensaje = millis();
      if (bsodMostrado) {
        setEstadoBuscando(tft); // Inicia en modo búsqueda al conectar
        bsodMostrado = false;
      }
      Serial.println("PONG");
    }
    else if (comando == "START_IMG") { recibirImagen(); }
    else if (comando == "SET_BUSCANDO") { ultimoMensaje = millis(); setEstadoBuscando(tft); }
    else if (comando == "SET_RECONOCIENDO") { ultimoMensaje = millis(); setEstadoReconociendo(tft); }
    else if (comando == "SET_VERIFICADO") { ultimoMensaje = millis(); setEstadoVerificado(tft); }
    else if (comando == "SET_NO_ENCONTRADO") { ultimoMensaje = millis(); setEstadoNoEncontrado(tft); }
    else if (comando == "SET_VENCIDO") { ultimoMensaje = millis(); setEstadoVencido(tft); }
  }
}