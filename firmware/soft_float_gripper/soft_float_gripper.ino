/*
 * Soft-Float Gripper - control firmware
 * Course 059250 Soft Robotics, Politecnico di Milano, A.Y. 2025/26
 *
 * Shadow-triggered closure of a 3-finger tendon-driven soft gripper.
 *  - LDR (photoresistor) in the palm detects the object's shadow
 *  - Digital servo winds the main tendon through a whiffletree
 *  - Button 1: first press = calibration, then = release / open
 *  - Button 2: forced closure (bypasses the sensor)
 *
 * Identifiers and serial messages are kept in Italian as in the original code.
 * (soglia = threshold, presaAttiva = grasp active, ombra = shadow,
 *  rilascio = release, chiusura forzata = forced closure)
 */

#include <Servo.h>

Servo servo;

// ====================================================
// PIN
// ====================================================

const int LDR_PIN       = A0;
const int SERVO_PIN     = 9;

const int BTN_PIN       = 2; // Pulsante rilascio/apertura  (release / open button)
const int BTN_FORZA_PIN = 3; // Pulsante chiusura forzata   (forced-closure button)

// ====================================================
// SERVO
// ====================================================

const int ANGOLO_APERTO = 180;  // open position  [deg]
const int ANGOLO_CHIUSO = 70;   // closed position [deg]  -> 110 deg stroke

// ====================================================
// TIMING
// ====================================================

const int DEBOUNCE_OMBRA = 150;   // shadow must persist this long [ms]
const int DEBOUNCE_BTN   = 200;   // button debounce [ms]
const int DELAY_RILASCIO = 3000;  // sensor lock-out after release [ms]

// ====================================================
// VARIABILI
// ====================================================

int soglia = 0;

bool presaAttiva = false;
bool calibrato   = false;

unsigned long tempoOmbra  = 0;
unsigned long ultimoClick = 0;

bool statoBtnPrecedente      = HIGH;
bool statoBtnForzaPrecedente = HIGH;

// ====================================================
// CALIBRAZIONE
// ====================================================

void calibra() {

  Serial.println("\n>> Calibrazione in corso...");

  delay(500);

  int valoreAmbiente = analogRead(LDR_PIN);

  // Trigger solo con ombra molto forte
  soglia = valoreAmbiente * 0.35;

  Serial.print(">> Valore ambiente: ");
  Serial.println(valoreAmbiente);

  Serial.print(">> Soglia impostata: ");
  Serial.println(soglia);

  Serial.println(">> Calibrazione completata!");
  Serial.println(">> Sistema pronto!\n");
}

// ====================================================
// RILASCIO
// ====================================================

void rilascia() {

  Serial.println("\n>> RILASCIO - apro le dita...");

  servo.write(ANGOLO_APERTO);

  Serial.println(">> Sensore temporaneamente disabilitato...");
  Serial.print(">> Attendo ");
  Serial.print(DELAY_RILASCIO / 1000);
  Serial.println(" secondi...\n");

  delay(DELAY_RILASCIO);

  presaAttiva = false;
  tempoOmbra = 0;

  Serial.println(">> Sensore riattivato, pronto!\n");
}

// ====================================================
// SETUP
// ====================================================

void setup() {

  Serial.begin(9600);

  servo.attach(SERVO_PIN);
  servo.write(ANGOLO_APERTO);

  pinMode(BTN_PIN, INPUT_PULLUP);
  pinMode(BTN_FORZA_PIN, INPUT_PULLUP);

  Serial.println("================================");
  Serial.println(" SISTEMA AVVIATO ");
  Serial.println(" Premi il pulsante per calibrare");
  Serial.println("================================\n");
}

// ====================================================
// LOOP
// ====================================================

void loop() {

  // ================================================
  // GESTIONE PULSANTE RILASCIO/APERTURA
  // ================================================

  bool statoBtn = digitalRead(BTN_PIN);

  // Rileva solo il click reale (HIGH -> LOW)
  if (statoBtnPrecedente == HIGH && statoBtn == LOW) {

    // Debounce software
    if (millis() - ultimoClick > DEBOUNCE_BTN) {

      ultimoClick = millis();

      // ----------------------------------------------
      // PRIMA PRESSIONE -> CALIBRAZIONE
      // ----------------------------------------------

      if (!calibrato) {

        calibra();
        calibrato = true;
      }

      // ----------------------------------------------
      // DOPO -> RILASCIO
      // ----------------------------------------------

      else if (presaAttiva) {

        rilascia();
      }
    }
  }

  statoBtnPrecedente = statoBtn;

  // ================================================
  // PULSANTE CHIUSURA FORZATA
  // ================================================

  bool statoBtnForza = digitalRead(BTN_FORZA_PIN);

  // Rileva click reale
  if (statoBtnForzaPrecedente == HIGH && statoBtnForza == LOW) {

    if (millis() - ultimoClick > DEBOUNCE_BTN) {

      ultimoClick = millis();

      // Solo se calibrato e non già chiuso
      if (calibrato && !presaAttiva) {

        Serial.println("\n>> CHIUSURA FORZATA!\n");

        presaAttiva = true;

        // Ignora il sensore
        tempoOmbra = 0;

        servo.write(ANGOLO_CHIUSO);
      }
    }
  }

  statoBtnForzaPrecedente = statoBtnForza;

  // ================================================
  // SE NON CALIBRATO O PRESA ATTIVA -> NON LEGGERE IL SENSORE
  // ================================================

  if (!calibrato) {
    delay(50);
    return;
  }

  if (presaAttiva) {
    delay(50);
    return;
  }

  // ================================================
  // LETTURA LDR
  // ================================================

  int ldrVal = analogRead(LDR_PIN);

  Serial.print("LDR: ");
  Serial.print(ldrVal);

  Serial.print("  |  Soglia: ");
  Serial.println(soglia);

  // ================================================
  // RILEVAMENTO OMBRA
  // ================================================

  if (ldrVal < soglia) {

    // Prima rilevazione ombra
    if (tempoOmbra == 0) {
      tempoOmbra = millis();
    }

    // Ombra stabile
    if (millis() - tempoOmbra > DEBOUNCE_OMBRA) {

      Serial.println("\n>> OGGETTO RILEVATO - chiudo le dita!\n");

      presaAttiva = true;

      servo.write(ANGOLO_CHIUSO);
    }
  }

  else {

    // Ombra sparita
    tempoOmbra = 0;
  }

  delay(50);
}
