/* ---------------------------------------------------------
   Sistema IoT Bivalvos – Tinkercad (LCD paralelo 16 pines)
   Sensores:
     TMP36  -> A0
     LDR    -> A1  (LDR a 5V, nodo->A1, 10k a GND)
     SAL    -> A2  (sensor de humedad del suelo: SIG→A2)
     Pulsador actividad -> D8 (a GND, INPUT_PULLUP)
   Actuadores:
     Buzzer -> D13
     LED_ALERT (rojo) -> D9 (+220Ω a GND)
     LED_ALIVE (verde) -> D10 (+220Ω a GND)
   LCD paralelo 16x2:
     RS D12, E D11, D4 D5, D5 D4, D6 D3, D7 D2
----------------------------------------------------------*/
#include <LiquidCrystal.h>

const int PIN_TMP36 = A0;
const int PIN_LDR   = A1;
const int PIN_SAL   = A2;
const int PIN_BTN   = 8;     // pulsador actividad
const int PIN_LED_ALERT = 9;
const int PIN_LED_ALIVE = 10;
const int PIN_BUZZ  = 13;

// LCD: RS, E, D4, D5, D6, D7
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

// ---- Suavizado simple
float tC_s  = 25.0;
int   tb_s  = 0;
int   sal_s = 0;

// ---- Parámetros de calibración del sensor de humedad del suelo
#define DEBUG_SAL false
const int RAW_SAL_DRY = 200;   // Lectura mínima (poca conductividad)
const int RAW_SAL_WET = 900;   // Lectura máxima (alta conductividad)

float smoothFloat(float nuevo, float previo, float alpha = 0.3) {
  return alpha * nuevo + (1.0 - alpha) * previo;
}
int smoothInt(int nuevo, int previo, float alpha = 0.3) {
  return (int)(alpha * nuevo + (1.0 - alpha) * previo);
}

// ---- Lecturas
float leerTemperaturaC() {
  int raw = analogRead(PIN_TMP36);
  float v = raw * 5.0 / 1023.0;
  return (v - 0.5) * 100.0;  // TMP36: 10mV/°C, offset 0.5V
}
int leerTurbidezScore() {
  int raw = analogRead(PIN_LDR);
  int inv = 1023 - raw;
  int score = map(inv, 0, 1023, 0, 100);
  return constrain(score, 0, 100);
}
int leerSalinidadScore() {
  int raw = analogRead(PIN_SAL);
  if (DEBUG_SAL) {
    Serial.print("[SAL raw]=");
    Serial.print(raw);
    Serial.print(" ");
  }
  int score = map(raw, RAW_SAL_DRY, RAW_SAL_WET, 0, 100);
  return constrain(score, 0, 100);
}

// ---- Clasificación por reglas
int clasificarBivalvo(float tC, int turb, int sal) {
  bool rangoTempOstra    = (tC >= 18 && tC <= 28);
  bool rangoTempMejillon = (tC >= 12 && tC <= 24);
  bool rangoTempAlmeja   = (tC >= 16 && tC <= 30);

  if (sal >= 70 && turb <= 60 && rangoTempOstra) return 1;      // OSTRA
  if (sal >= 40 && sal <= 75 && turb >= 50 && turb <= 85 && rangoTempMejillon) return 2; // MEJILLON
  if (sal <= 50 && turb >= 40 && rangoTempAlmeja) return 3;     // ALMEJA
  return 0; // NONE
}

// ---- Actividad biológica simulada
unsigned long lastActivityMs = 0;
const unsigned long NO_ACTIVITY_TIME = 120000UL; // 2 minutos

bool hayActividadReciente() {
  return (millis() - lastActivityMs) < NO_ACTIVITY_TIME;
}

bool readButtonFalling() {
  static bool prev = true;
  bool now = digitalRead(PIN_BTN);
  bool falling = (prev == true && now == false);
  prev = now;
  return falling;
}

// Pitido sin saturar
unsigned long lastBeep = 0;
void beepOk() {
  if (millis() - lastBeep > 250) { tone(PIN_BUZZ, 1200, 80); lastBeep = millis(); }
}
void beepWarn() {
  if (millis() - lastBeep > 250) { tone(PIN_BUZZ, 420, 160); lastBeep = millis(); }
}

// ---- Setup
void setup() {
  pinMode(PIN_BUZZ, OUTPUT);
  pinMode(PIN_BTN, INPUT_PULLUP);
  pinMode(PIN_LED_ALERT, OUTPUT);
  pinMode(PIN_LED_ALIVE, OUTPUT);

  Serial.begin(9600);
  lcd.begin(16, 2);
  lcd.print("Bivalvos IoT");
  lcd.setCursor(0,1);
  lcd.print("Inicializando");
  delay(900);
  lcd.clear();

  lastActivityMs = millis();
}

// ---- Loop
void loop() {
  float tC   = leerTemperaturaC();
  int   turb = leerTurbidezScore();
  int   sal  = leerSalinidadScore();

  // suavizado
  tC_s  = smoothFloat(tC,  tC_s);
  tb_s  = smoothInt(turb, tb_s);
  sal_s = smoothInt(sal,  sal_s);

  int tipo = clasificarBivalvo(tC_s, tb_s, sal_s);

  // registrar pulsación del botón
  if (readButtonFalling()) {
    lastActivityMs = millis();
    tone(PIN_BUZZ, 1500, 50);
  }

  bool vivo = hayActividadReciente();

  // ---- LEDs
  digitalWrite(PIN_LED_ALIVE, vivo ? HIGH : LOW);
  if (!vivo || tipo == 0) digitalWrite(PIN_LED_ALERT, HIGH);
  else digitalWrite(PIN_LED_ALERT, LOW);

  // ---- LCD
  lcd.setCursor(0,0);
  lcd.print("T:");
  lcd.print(tC_s,1);
  lcd.print("C Tb:");
  lcd.print(tb_s);
  lcd.setCursor(0,1);
  lcd.print("Sa:");
  lcd.print(sal_s);
  lcd.print("% ");

  if (!vivo) lcd.print("SIN ACT");
  else if (tipo == 1) { lcd.print("OSTRA   ");    beepOk(); }
  else if (tipo == 2) { lcd.print("MEJILLON");    beepOk(); }
  else if (tipo == 3) { lcd.print("ALMEJA  ");    beepOk(); }
  else                { lcd.print("AJUSTAR ");    beepWarn(); }

  // ---- Serial JSON
  Serial.print("{\"tempC\":");   Serial.print(tC_s,1);
  Serial.print(",\"turbidez\":");Serial.print(tb_s);
  Serial.print(",\"salinidad\":");Serial.print(sal_s);
  Serial.print(",\"vivo\":");    Serial.print(vivo?"true":"false");
  Serial.print(",\"clasif\":\"");
  if (tipo==1) Serial.print("OSTRA");
  else if (tipo==2) Serial.print("MEJILLON");
  else if (tipo==3) Serial.print("ALMEJA");
  else Serial.print("NONE");
  Serial.println("\"}");

  delay(700);
}
