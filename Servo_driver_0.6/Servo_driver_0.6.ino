/*
Developed by Igor Kozlowski
in May 2016
-soft start
-stall protection
=============================================
Input (serial):
R+/-255;L+/-255[;C128000/E/D]\n

Output (serial):
R int Req_RPM;int PWR;; int RPM
L int Req_RPM;int PWR;; int RPM
=============================================

MR - right motor
ML - left motor
CV - Camera vertical
CH - Camera horizontal
*/

 #include <Servo.h>

 #define VER "0.59"
 #define COMM_BITRATE 57600
 #define RIGHT 1
 #define LEFT 0
 #define HORIZONTAL 1
 #define VERTICAL 0
 #define PRECISION 25
 #define RESOLUTION 250
 #define SMOOTH_FACTOR 100
// #define COMM_BITSHIFT 30

// PWM GPIO: 3, 5 ,6 ,9 , 10, 11

 #define SensorMR_Pin 3
 #define SensorML_Pin 2
 
 #define CamH_Pin 9
 #define CamV_Pin 10

 #define ProxTrig_Pin 6
 #define ProxEcho_Pin A7

 #define SensorCurr_Pin 2
 #define SensorVolt_Pin 1
 #define Laser_Pin 13

 unsigned long Last_communication_time;
 
 volatile unsigned long PulseTime[2];
 volatile unsigned long PulseTime_prev[2];

 int counter;
 int Voltage;
 int Current;
 int CamHV[2];
 int Pwr[2];
 int Comm_buffer[6];
 int Ctr1_Pin[]     = {4,8};
 int Ctr2_Pin[]     = {7,12};
 int Pwm_Pin[]      = {5,11};
 int Required_Rpm[] = {50,50};
 unsigned int Distance;
 unsigned int Comm_resp[16];
 unsigned int Rpm[2];
 unsigned int Rpm_prev[2];
 unsigned long decmillis;
 boolean Executed   = false;
 boolean CV_read    = false;

 /********* Init servo *******/
 Servo CamH;
 Servo CamV;
/**************** ISR ************************************/

 void Hall_R_tick()//This function is called whenever a magnet/interrupt is detected by the arduino
 {
    GetTickTime(RIGHT);
 }

 void Hall_L_tick()//This function is called whenever a magnet/interrupt is detected by the arduino
 {
    GetTickTime(LEFT);
 }

 void GetTickTime(boolean RL)
 {
    PulseTime_prev[RL] = PulseTime[RL];
    PulseTime[RL] = micros() / PRECISION;
 }

/*********************************************************/

 void Set_Motor(boolean RL, boolean Stall_RL, boolean Stall_OT)
 {
    boolean Direction = LOW;
    if (Required_Rpm[RL] > 50) {
      Direction = HIGH;
    }
    int Req_Rpm = abs(Required_Rpm[RL] - 50) * 10; // 0-500 (2 * RESOLUTION)

    if ( Req_Rpm > 0 && Stall_RL == false) {
      digitalWrite(Ctr1_Pin[RL], !Direction);
      digitalWrite(Ctr2_Pin[RL], Direction);

      // Reduce power once gear runs
      if (Rpm_prev[RL] == 0) {
        if (Rpm[RL] > 0) {
//          Pwr[RL] -= 50;
          Pwr[RL] = int(Pwr[RL] * 0.5);
          Rpm[RL] /= 2;
        }
        else {
          Pwr[RL] += 200;
        }
      }

      // Rpm_diff will be positive on low Rpm
      int Rpm_diff = Req_Rpm - Rpm[RL];

      // Rpm_incr will be negative on Rpm drop down
      int Rpm_incr = (Rpm[RL] - Rpm_prev[RL]) * 5;

      // Rpm Predicted
      int Rpm_pred = Rpm[RL] + Rpm_incr;

      Pwr[RL] += Rpm_diff + 10;

      if (Req_Rpm > Rpm_pred) {
        Pwr[RL] += abs(Rpm_diff) + 5;
      }
      else if (Req_Rpm < Rpm_pred) {
        Pwr[RL] -= abs(Rpm_diff) - 5;
      }

      int M_Power = 0;
      if (Pwr[RL] > 0) {
        M_Power = int(Pwr[RL] / SMOOTH_FACTOR  / (1 + Stall_OT));
        if (M_Power > RESOLUTION) M_Power = RESOLUTION;
      }
      analogWrite(Pwm_Pin[RL], M_Power);
    }
    else {
      // STOP requested!!!
      digitalWrite(Ctr1_Pin[RL], LOW);
      digitalWrite(Ctr2_Pin[RL], LOW);
      Pwr[RL] = 0;
    }
 }

 boolean DetectStall(boolean RL)
 {
    if ( Pwr[RL] != 0 ) {
      if (Rpm[RL] == 0) {
        unsigned int Break_time = abs((micros() - PulseTime_prev[RL]) / 50) ;
        if ( Break_time >= 50000 ) { // Stall after about 2500ms; removed "&& abs(RequiredMR_Power) >= 10"
          Rpm[RL] = 0;
          return true;
        }
      }
    }
//    else {
//      if (Required_Rpm[RL] == 0) {
//        Rpm[RL] = 0;
//        Rpm_prev[RL] = Rpm[RL];
//      }
//    }
    return false;
 }

 void establishContact()
 {
    String Text = "DEVICE READY(";
    Text += VER;
    Text += ")";
    Serial.println("IVO-A1:" + Text);
    while (!Serial.available()) {
      delay(100);
    }
    Last_communication_time = millis();
 }

boolean flushBuffer(int lenght)
{
//  int lenght = Serial.available()
  for (int i = 0 ; i <= lenght ; i++) {
    Serial.read();
  }
}

boolean ReadSerialData(int Buf_len)
{
  int StartChar = int(Serial.read());    // 1
  if ( StartChar == 255 ) {
    Comm_buffer[0] = int(Serial.read()); // 2
    Comm_buffer[1] = int(Serial.read()); // 3
    Comm_buffer[2] = int(Serial.read()); // 4
    Comm_buffer[3] = int(Serial.read()); // 5
    Comm_buffer[4] = int(Serial.read()); // 6
    Comm_buffer[5] = int(Serial.read()); // 7
    int EndChar = int(Serial.read());    // 8
    if ( EndChar == 255 ) {
      int CTRL1_Mask;
      int CTRL2_Mask;

      counter = 0;
      while ( counter < 6 ) {
        if ( Comm_buffer[counter] == 252 ) Comm_buffer[counter] = 17;
        else if ( Comm_buffer[counter] == 253 ) Comm_buffer[counter] = 19;
        counter ++;
      }

      Required_Rpm[RIGHT]     = Comm_buffer[0]; // 1
      Required_Rpm[LEFT]      = Comm_buffer[1]; // 2
      CamHV[HORIZONTAL]       = Comm_buffer[2]; // 3
      CamHV[VERTICAL]         = Comm_buffer[3]; // 4
      CTRL1_Mask              = Comm_buffer[4]; // 5
      CTRL2_Mask              = Comm_buffer[5]; // 6

      boolean lights    = bitRead(CTRL1_Mask,8);
//        boolean speakers  = bitRead(CTRL1_Mask,7);
//        boolean mic       = bitRead(CTRL1_Mask,6);
//        boolean disp      = bitRead(CTRL1_Mask,5);
      boolean laser     = bitRead(CTRL1_Mask,4);
      boolean AutoMode  = bitRead(CTRL1_Mask,3);
      Last_communication_time = decmillis;
      return true;
    }
    else {
      Serial.print("BADEND_________" + String(EndChar));
      flushBuffer(Buf_len - 8);
    }
    return false;
  }
  else {
    Serial.print("BADSTART_______" + String(StartChar));
    flushBuffer(Buf_len - 8);
  }

}

double GetDistance()
{
    digitalWrite(ProxTrig_Pin, HIGH);
    delayMicroseconds(10);
    digitalWrite(ProxTrig_Pin, LOW);
    return pulseIn(ProxEcho_Pin, HIGH, 16000);
}

/*********************************************************/
 
 void setup()
 {
   Serial.begin(COMM_BITRATE);

   while (!Serial) {
     ; // wait for serial port to connect. Needed for native USB port only
   }
   
   pinMode(SensorMR_Pin, INPUT);
   pinMode(Pwm_Pin[RIGHT], OUTPUT);
   pinMode(Ctr1_Pin[RIGHT], OUTPUT);
   pinMode(Ctr2_Pin[RIGHT], OUTPUT);

   pinMode(SensorML_Pin, INPUT);
   pinMode(Pwm_Pin[LEFT], OUTPUT);
   pinMode(Ctr1_Pin[LEFT], OUTPUT);
   pinMode(Ctr2_Pin[LEFT], OUTPUT);

   pinMode(ProxTrig_Pin, OUTPUT);
   pinMode(ProxEcho_Pin, INPUT);

   CamH.attach(CamH_Pin);
   CamV.attach(CamV_Pin);
//   CamH.write(60);
//   CamV.write(100);

   digitalWrite(ProxTrig_Pin, LOW);
   attachInterrupt(digitalPinToInterrupt(SensorMR_Pin), Hall_R_tick, RISING);//Initialize the intterrupt pin (Arduino digital pin 2)
   attachInterrupt(digitalPinToInterrupt(SensorML_Pin), Hall_L_tick, RISING);//Initialize the intterrupt pin (Arduino digital pin 3)

   establishContact();
}
 
/*********************************************************/

 void loop()//Measure RPM & PWR
 {
    boolean Stall[] = {false,false};
    boolean Debug = false;
    boolean SendCommit = false;

    int Buf_len = Serial.available();
    if (Buf_len >= 8) {
      SendCommit = ReadSerialData(Buf_len);
    }

    decmillis = millis() / 5;
    if ( decmillis - Last_communication_time > 200 ) { // communication breakdown for 1,0 sec.
      if ( Last_communication_time < decmillis ) {
        Required_Rpm[RIGHT] = 50;
        Required_Rpm[LEFT] = 50;
        Set_Motor(RIGHT,HIGH,HIGH);
        Set_Motor(LEFT,HIGH,HIGH);
        establishContact();
        exit;
      }
    }

    if ( decmillis % 2 == 0 ) {
      if ( Executed == false ) {
        Executed = true;
    
        if ((micros() / PRECISION) - PulseTime_prev[RIGHT] > 50000) {
          Rpm[RIGHT] = 0;
          Rpm_prev[RIGHT] = 0;
        }
        else {
          Rpm_prev[RIGHT] = Rpm[RIGHT];
          Rpm[RIGHT] = 60000 / (PulseTime[RIGHT] - PulseTime_prev[RIGHT]);
        }
    
        if ((micros() / PRECISION) - PulseTime_prev[LEFT] > 50000) {
          Rpm[LEFT] = 0;
          Rpm_prev[LEFT] = 0;
        }
        else {
          Rpm_prev[LEFT] = Rpm[LEFT];
          Rpm[LEFT] = 60000 / (PulseTime[LEFT] - PulseTime_prev[LEFT]);
        }
    
        Stall[RIGHT] = DetectStall(RIGHT);
        Stall[LEFT] = DetectStall(LEFT);

    //                              *** call motor exec ***
        Set_Motor(RIGHT, Stall[RIGHT], Stall[LEFT]);
        Set_Motor(LEFT, Stall[LEFT], Stall[RIGHT]);
      }
    }
    else {
      Executed = false;
    }

//  Get utilized Current and battery Voltage every 1/10sec.
    if (decmillis % 20 == 0 ) {
      if (CV_read == false) {
        CV_read = true;
        Current = analogRead(SensorCurr_Pin);
        Voltage = analogRead(SensorVolt_Pin);

//      Get Distance from US sensor
        if (decmillis % 100 == 0 ) {
          Distance = GetDistance();
        }
      }
    }
    else {
      CV_read = false;
    }

//                              *** generate driver response ***
    if ( SendCommit == true ) {
      Comm_resp[0] = 255;                             // 1
      Comm_resp[1] = int(Pwr[RIGHT] / SMOOTH_FACTOR); // 2
      Comm_resp[2] = int(Pwr[LEFT] / SMOOTH_FACTOR);  // 3
      Comm_resp[3] = int(Rpm[RIGHT] / 2);             // 4
      Comm_resp[4] = int(Rpm[LEFT] / 2);              // 5
      Comm_resp[5] = int(Current / RESOLUTION);       // 6
      Comm_resp[6] = Current % RESOLUTION;            // 7
      Comm_resp[7] = int(Voltage / RESOLUTION);       // 8
      Comm_resp[8] = Voltage % RESOLUTION;            // 9
      Comm_resp[9] = int(Distance / RESOLUTION);      // 10
      Comm_resp[10] = Distance % RESOLUTION;          // 11
      Comm_resp[11] = 0;                              // 12
      Comm_resp[12] = 0;                              // 13
      Comm_resp[13] = 0;                              // 14
      Comm_resp[14] = 0;                              // 15
//      Comm_resp[13] = Required_Rpm_tmp[RIGHT];        // 14
//      Comm_resp[14] = Required_Rpm_tmp[LEFT];         // 15
      Comm_resp[15] = 255;                            // 16

      counter = 1;
      int xchr = 0;
      Serial.write(Comm_resp[0]);
      while ( counter < 15 ) {
        xchr = Comm_resp[counter];
        if ( xchr == 17 ) xchr = 252;
        else if ( xchr == 19 ) xchr = 253;
        Serial.write(xchr);
        counter ++;
      }
      Serial.write(Comm_resp[15]);

      if (CamHV[HORIZONTAL] != 0) CamH.write(CamHV[HORIZONTAL]);
      if (CamHV[VERTICAL] != 0) CamV.write(CamHV[VERTICAL]);        
    }
//    Rpm_prev[RIGHT] = Rpm[RIGHT];
//    Rpm_prev[LEFT] = Rpm[LEFT];
    delay(1);
 }


