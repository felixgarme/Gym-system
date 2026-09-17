#ifndef ANIMACIONES_H
#define ANIMACIONES_H

#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>

// Definición de los estados visuales
enum EstadoUI {
  ESTADO_DESCONECTADO,
  ESTADO_BUSCANDO,
  ESTADO_RECONOCIENDO,
  ESTADO_VERIFICADO,
  ESTADO_NO_ENCONTRADO,
  ESTADO_VENCIDO,
  ESTADO_IMAGEN
};

EstadoUI estadoActual = ESTADO_DESCONECTADO;

// Variables generales y temporizadores
int puntosAnimacion = 0;
unsigned long proxBlink = 0;
bool ojosCerrados = false;
unsigned long tiempoCierre = 0;
int offsetX_ojos = 0;
unsigned long ultimoToggleTexto = 0;
bool textoVisible = true;

// Nuevas variables para animaciones fluidas
unsigned long ultimoSpinnerUpdate = 0;
int frameSpinner = 0;
unsigned long ultimoRainbowUpdate = 0;
byte indiceRainbow = 0;
uint16_t colorArcoirisActual = 0;

// Paleta de colores futuristas
const uint16_t COLOR_AMARILLO = 0xFFE0;
const uint16_t COLOR_VERDE    = 0x07E0;
const uint16_t COLOR_ROJO     = 0xF800;
const uint16_t COLOR_NARANJA  = 0xFD20;

// ================= FUNCIONES DE DIBUJO Y UTILIDAD =================

// Generador de colores para el arcoíris fluido (RGB565)
uint16_t colorWheel(Adafruit_ST7789 &tft, byte pos) {
  pos = 255 - pos;
  if (pos < 85) { return tft.color565(255 - pos * 3, 0, pos * 3); }
  if (pos < 170) { pos -= 85; return tft.color565(0, pos * 3, 255 - pos * 3); }
  pos -= 170; return tft.color565(pos * 3, 255 - pos * 3, 0);
}

// Función vaciada para evitar errores de compilación
void actualizarAnimacionBusqueda(Adafruit_ST7789 &tft) {
  // Eliminado intencionalmente
}

void mostrarBSOD(Adafruit_ST7789 &tft) {
  estadoActual = ESTADO_DESCONECTADO;
  tft.fillScreen(0x001F);
  tft.setTextColor(0xFFFF); 
  tft.setTextSize(6); tft.setCursor(15, 30); tft.print(":(");
  tft.setTextSize(2); tft.setCursor(15, 100); tft.println("Desconectado.");
  tft.setTextSize(1); tft.setCursor(15, 140); tft.println("Conecta el USB-C.");
}

// Marco "Viewfinder" tipo cámara futurista
void dibujarMarco(Adafruit_ST7789 &tft, uint16_t color) {
  int t = 4;  // Grosor de la línea más fino (profesional)
  int l = 35; // Longitud de la esquina adaptada
  // Arriba Izquierda
  tft.fillRect(30, 30, l, t, color); tft.fillRect(30, 30, t, l, color);
  // Arriba Derecha
  tft.fillRect(210-l, 30, l, t, color); tft.fillRect(210-t, 30, t, l, color);
  // Abajo Izquierda
  tft.fillRect(30, 210-t, l, t, color); tft.fillRect(30, 210-l, t, l, color);
  // Abajo Derecha
  tft.fillRect(210-l, 210-t, l, t, color); tft.fillRect(210-t, 210-l, t, l, color);
}

// Dibuja el texto centrado ADENTRO del recuadro
void dibujarTextoAbajo(Adafruit_ST7789 &tft, String texto, uint16_t color) {
  int16_t x1, y1; uint16_t w, h;
  tft.setTextSize(2); // Texto grande
  tft.getTextBounds(texto, 0, 0, &x1, &y1, &w, &h);
  tft.setTextColor(color);
  tft.setCursor(120 - w/2, 180); 
  tft.print(texto);
}

// Limpia toda la pantalla y prepara el marco base para un nuevo estado estático
void limpiarYDibujarBase(Adafruit_ST7789 &tft, uint16_t color, String texto) {
  tft.fillScreen(0x0000); 
  dibujarMarco(tft, color);
  dibujarTextoAbajo(tft, texto, color);
}

// Dibuja el símbolo de Check (✓) masivo para el acceso concedido
void dibujarCheck(Adafruit_ST7789 &tft, uint16_t color) {
  for(int i = 0; i < 8; i++) {
    tft.drawLine(80, 110-i, 105, 135-i, color); // Trazo corto
    tft.drawLine(105, 135-i, 160, 75-i, color); // Trazo largo
  }
}


// ================= CONFIGURACIÓN DE ESTADOS =================

void setEstadoBuscando(Adafruit_ST7789 &tft) {
  if(estadoActual == ESTADO_BUSCANDO) return;
  estadoActual = ESTADO_BUSCANDO;
  tft.fillScreen(0x0000); 
  ojosCerrados = false;
  offsetX_ojos = 0;
  proxBlink = millis() + 500;
  ultimoRainbowUpdate = 0; 
}

void setEstadoReconociendo(Adafruit_ST7789 &tft) {
  if(estadoActual == ESTADO_RECONOCIENDO) return;
  estadoActual = ESTADO_RECONOCIENDO;
  limpiarYDibujarBase(tft, COLOR_AMARILLO, "ANALIZANDO...");
  frameSpinner = 0;
  ultimoSpinnerUpdate = millis();
  ultimoToggleTexto = millis();
}

void setEstadoVerificado(Adafruit_ST7789 &tft) {
  if(estadoActual == ESTADO_VERIFICADO) return;
  estadoActual = ESTADO_VERIFICADO;
  limpiarYDibujarBase(tft, COLOR_VERDE, "VERIFICADO");
  dibujarCheck(tft, COLOR_VERDE);
}

void setEstadoNoEncontrado(Adafruit_ST7789 &tft) {
  if(estadoActual == ESTADO_NO_ENCONTRADO) return;
  estadoActual = ESTADO_NO_ENCONTRADO;
  limpiarYDibujarBase(tft, COLOR_ROJO, "DESCONOCIDO");
  
  tft.setTextSize(10);
  tft.setTextColor(COLOR_ROJO);
  tft.setCursor(90, 65); 
  tft.print("?");
}

void setEstadoVencido(Adafruit_ST7789 &tft) {
  if(estadoActual == ESTADO_VENCIDO) return;
  estadoActual = ESTADO_VENCIDO;
  limpiarYDibujarBase(tft, COLOR_NARANJA, "VENCIDO");
  
  // Ojos robóticos rectos y serios (sin cara)
  tft.fillRoundRect(65, 110, 40, 10, 4, COLOR_NARANJA);
  tft.fillRoundRect(135, 110, 40, 10, 4, COLOR_NARANJA);
}

void apagarFaceID() {
  estadoActual = ESTADO_IMAGEN;
}


// ================= MOTOR DE ANIMACIONES =================

void animarFaceID(Adafruit_ST7789 &tft) {
  
  // --- 1. Animación BUSCANDO (Ojos robóticos elegantes con Arcoíris fluido) ---
  if (estadoActual == ESTADO_BUSCANDO) {
    
    // Lógica de Tiempos de Parpadeo
    if (!ojosCerrados && millis() > proxBlink) {
       ojosCerrados = true;
       tiempoCierre = millis();
       // Borra el área amplia donde estaban los ojos abiertos
       tft.fillRect(50, 90, 140, 55, 0x0000); 
    } 
    else if (ojosCerrados && millis() - tiempoCierre > 150) {
       ojosCerrados = false;
       offsetX_ojos = random(-12, 13); // Movimiento lateral de los ojos
       proxBlink = millis() + random(1500, 4000);
       // Borra el área de los ojos cerrados
       tft.fillRect(50, 90, 140, 55, 0x0000); 
    }

    // Dibujado ultra-rápido del Arcoíris
    if (millis() - ultimoRainbowUpdate > 20) {
       indiceRainbow += 2;
       colorArcoirisActual = colorWheel(tft, indiceRainbow);
       
       dibujarMarco(tft, colorArcoirisActual);

       // Dibujar Ojos Profesionales estilo "Smart Assistant"
       if (ojosCerrados) {
         // Ojos cerrados (líneas suaves y finas)
         tft.fillRoundRect(70, 115, 35, 8, 4, colorArcoirisActual); 
         tft.fillRoundRect(135, 115, 35, 8, 4, colorArcoirisActual);
       } else {
         // Ojos abiertos (cápsulas verticales redondeadas)
         tft.fillRoundRect(70 + offsetX_ojos, 95, 35, 45, 15, colorArcoirisActual);
         tft.fillRoundRect(135 + offsetX_ojos, 95, 35, 45, 15, colorArcoirisActual);
       }

       ultimoRainbowUpdate = millis();
    }
  }

  // --- 2. Animación RECONOCIENDO (Spinner de rueda) ---
  if (estadoActual == ESTADO_RECONOCIENDO) {
     if (millis() - ultimoSpinnerUpdate > 80) { 
        int cx = 120, cy = 100, r = 35; 
        for (int i = 0; i < 8; i++) {
            float angle = i * 3.14159 / 4.0;
            int x = cx + cos(angle) * r;
            int y = cy + sin(angle) * r;
            uint16_t colorPunto = (i == frameSpinner) ? COLOR_AMARILLO : tft.color565(60, 60, 0); 
            tft.fillCircle(x, y, 6, colorPunto);
        }
        frameSpinner = (frameSpinner + 1) % 8;
        ultimoSpinnerUpdate = millis();
     }

     // Texto inferior parpadeando
     if (millis() - ultimoToggleTexto > 400) {
        String texto = "ANALIZANDO...";
        int16_t x1, y1; uint16_t w, h;
        tft.setTextSize(2);
        tft.getTextBounds(texto, 0, 0, &x1, &y1, &w, &h);
        
        if (textoVisible) {
          tft.fillRect(120 - w/2, 180, w, h, 0x0000); 
          textoVisible = false;
        } else {
          dibujarTextoAbajo(tft, texto, COLOR_AMARILLO);
          textoVisible = true;
        }
        ultimoToggleTexto = millis();
     }
  }
}
#endif