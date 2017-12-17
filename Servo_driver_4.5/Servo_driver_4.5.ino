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

 #define VER "0.55"
 #define COMM_BITRATE 115200
 #define RIGHT 1
 #define LEFT 0
 #define HORIZONTAL 1
 #define VERTICAL 0
 #define PRECISION 10
 #define RESOLUTION 250
 #define SMOOTH_FACTOR 3
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
 
 volatile unsigned long ChangeTime_prev[] = {0,0};
 volatile unsigned int Rpm[] = {0,0};
 volatile unsigned int Rpm_prev[] = {0,0};

 int Ctr1_Pin[]     = {4,8};
 int Ctr2_Pin[]     = {7,12};
 int Pwm_Pin[]      = {5,11};

 int Required_Rpm[] = {50,50};
 int Pwr[]          = {0,0};
 int Voltage        = 0;
 int Current        = 0;
 boolean Executed   = false;
 boolean CV_read    = false;
 unsigned int Distance = 0;
 unsigned int Comm_resp[16];
 /********* Init servo *******/
 Servo CamH;
 Servo CamV;
/**************** ISR ************************************/

 void HallMR_detect()//This function is called whenever a magnet/interrupt is detected by the arduino
 {
    GetRpm(RIGHT);
 }

 void HallML_detect()//This function is called whenever a magnet/interrupt is detected by the arduino
 {
    GetRpm(LEFT);
 }

 int GetRpm(boolean RL)
 {
    unsigned long ChangeTime = micros() / PRECISION;
    unsigned long Elapsed = ChangeTime - ChangeTime_prev[RL];

    Rpm_prev[RL] = Rpm[RL];
    Rpm[RL] += 30000 / Elapsed;
    Rpm[RL] /= 2;

    ChangeTime_prev[RL] = ChangeTime;
 }

/*********************************************************/

 void Set_Motor(boolean RL, boolean Stall_RL, boolean Stall_OT)
 {
    boolean Direction = LOW;
    int Req_Rpm = 5 * (Required_Rpm[RL] - 50);

    if (Req_Rpm > 0) {
      Direction = HIGH;
    }

    // Reduce power once gear runs
    if (Rpm_prev[RL] == 0 && Rpm[RL] != 0) {
      Pwr[RL] -= 15;
    }

    if ( Req_Rpm != 0 && Stall_RL == false) {
      digitalWrite(Ctr1_Pin[RL], !Direction);
      digitalWrite(Ctr2_Pin[RL], Direction);

      int Prediction_cnt = 11 - (Rpm[RL] / 25);
      int Rpm_Predicted = constrain((Prediction_cnt * Rpm[RL]) - ((Prediction_cnt - 1) * Rpm_prev[RL]),0,RESOLUTION);

      int Rpm_diff = (abs(Req_Rpm) - Rpm[RL]) / 3;

      if (Rpm[RL] > 5) {
        if (Rpm_Predicted > abs(Req_Rpm)) {
            Pwr[RL] -= constrain(Rpm_diff,-5,5);
        }
        else if (Rpm_Predicted < abs(Req_Rpm)) {
            Pwr[RL] += constrain(Rpm_diff,-5,5);
        }
      }
//      else if (Rpm[RL] > 10) {
//        Pwr[RL] += constrain(Rpm_diff,-2,2);
//      }
      else {
        Pwr[RL] += constrain(Rpm_diff,-5,5);
      }

      Pwr[RL] = constrain(Pwr[RL], 0, RESOLUTION * SMOOTH_FACTOR);

      analogWrite(Pwm_Pin[RL], int((Pwr[RL] / (1 + Stall_OT)) / SMOOTH_FACTOR));
    }
    else { //STOP!!!
      digitalWrite(Ctr1_Pin[RL], LOW);
      digitalWrite(Ctr2_Pin[RL], LOW);
      Pwr[RL] = 0;
    }
 }

 boolean DetectStall(boolean RL)
 {
    if ( Pwr[RL] != 0 ) {
      if (Rpm[RL] == 0) {
        unsigned int Break_time = abs((micros() - ChangeTime_prev[RL]) / 50) ;
        if ( Break_time >= 50000 ) { // Stall after about 2500ms; removed "&& abs(RequiredMR_Power) >= 10"
          Rpm[RL] = 0;
          Rpm_prev[RL] = Rpm[RL];
          return true;
        }
      }
    }
    else {
      if (Required_Rpm[RL] == 0) {
        Rpm[RL] = 0;
        Rpm_prev[RL] = Rpm[RL];
      }
    }
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

double GetDistance()
{
    digitalWrite(ProxTrig_Pin, HIGH);
    delayMicroseconds(10);
    digitalWrite(ProxTrig_Pin, LOW);
    return pulseIn(ProxEcho_Pin, HIGH, 16000);
}

boolean flushBuffer(int lenght)
{
//  int lenght = Serial.available()
  for (int i = 0 ; i <= lenght ; i++) {
    Serial.read();
  }
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
   attachInterrupt(digitalPinToInterrupt(SensorMR_Pin), HallMR_detect, CHANGE);//Initialize the intterrupt pin (Arduino digital pin 2)
   attachInterrupt(digitalPinToInterrupt(SensorML_Pin), HallML_detect, CHANGE);//Initialize the intterrupt pin (Arduino digital pin 3)

   establishContact();
}
 
/*********************************************************/

 void loop()//Measure RPM & PWR
 {
    boolean Stall[] = {false,false};
    boolean Debug = false;
    boolean SendCommit = false;
    int Required_Rpm_tmp[] = {0,0};
    Required_Rpm_tmp[RIGHT] = Required_Rpm[RIGHT];
    Required_Rpm_tmp[LEFT] = Required_Rpm[LEFT];

    int Buf_len = Serial.available();
    if (Buf_len >= 16) {
      int CTRL1_Mask;
      int CTRL2_Mask;
      int CamHV_tmp[] = {0,0};

      int StartChar = int(Serial.read());             // 1
      if ( StartChar == 255 ) {
        Required_Rpm_tmp[RIGHT] = int(Serial.read()); // 2
        Required_Rpm_tmp[LEFT]  = int(Serial.read()); // 3
        CamHV_tmp[HORIZONTAL]   = int(Serial.read()); // 4
        CamHV_tmp[VERTICAL]     = int(Serial.read()); // 5
        CTRL1_Mask  = int(Serial.read());             // 6
        CTRL2_Mask  = int(Serial.read());             // 7
        Serial.read();                                // 8
        Serial.read();                                // 9
        Serial.read();                                // 10
        Serial.read();                                // 11
        Serial.read();                                // 12
        Serial.read();                                // 13
        Serial.read();                                // 14
        Serial.read();                                // 15
        int EndChar = int(Serial.read());             // 16
        if ( EndChar == 255 ) {
          boolean lights    = bitRead(CTRL1_Mask,8);
//        boolean speakers  = bitRead(CTRL1_Mask,7);
//        boolean mic       = bitRead(CTRL1_Mask,6);
//        boolean disp      = bitRead(CTRL1_Mask,5);
          boolean laser     = bitRead(CTRL1_Mask,4);
          boolean AutoMode  = bitRead(CTRL1_Mask,3);
          Required_Rpm[RIGHT] = Required_Rpm_tmp[RIGHT];
          Required_Rpm[LEFT] = Required_Rpm_tmp[LEFT];
          if (CamHV_tmp[HORIZONTAL] != 0) CamH.write(CamHV_tmp[HORIZONTAL]);
          if (CamHV_tmp[VERTICAL] != 0) CamV.write(CamHV_tmp[VERTICAL]);        
          Last_communication_time = millis();
          SendCommit = true;
        }
        else {
          Serial.print("BADEND_________" + String(EndChar));
          flushBuffer(Buf_len - 16);
        }
      }
      else {
        Serial.print("BADSTART_______" + String(StartChar));
        flushBuffer(Buf_len - 16);
      }
    }

    if ( millis() - Last_communication_time > 1000 ) { // communication breakdown for 1,0 sec.
      if ( Last_communication_time < millis() ) {
        Required_Rpm[RIGHT] = 50;
        Required_Rpm[LEFT] = 50;
        Set_Motor(RIGHT,HIGH,HIGH);
        Set_Motor(LEFT,HIGH,HIGH);
        establishContact();
        exit;
      }
    }

    if (((millis()/5) % 2) == 0 ) {
      if ( Executed == false ) {
        Executed = true;
    
        if ((micros() / PRECISION) - ChangeTime_prev[RIGHT] > 10000) {
          Rpm[RIGHT] = 0;
          Rpm_prev[RIGHT] = 0;
        }
    
        if ((micros() / PRECISION) - ChangeTime_prev[LEFT] > 10000) {
          Rpm[LEFT] = 0;
          Rpm_prev[LEFT] = 0;
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
    if (((millis()/10) % 10) == 0 ) {
      if (CV_read == false) {
        CV_read = true;
        Current = analogRead(SensorCurr_Pin);
        Voltage = analogRead(SensorVolt_Pin);

//      Get Distance from US sensor
        if (((millis()/10) % 50) == 0 ) {
          Distance = GetDistance();
        }
      }
    }
    else {
      CV_read = false;
    }

//                              *** generate driver response ***
    if ( SendCommit == true ) {
      Comm_resp[0] = 255;                            // 1
      Comm_resp[1] = int(Pwr[RIGHT] / SMOOTH_FACTOR); // 2
      Comm_resp[2] = int(Pwr[LEFT] / SMOOTH_FACTOR);  // 3
      Comm_resp[3] = constrain(Rpm[RIGHT],0,RESOLUTION); // 4
      Comm_resp[4] = constrain(Rpm[LEFT],0,RESOLUTION);  // 5
      Comm_resp[5] = int(Current / RESOLUTION);       // 6
      Comm_resp[6] = Current % RESOLUTION;            // 7
      Comm_resp[7] = int(Voltage / RESOLUTION);       // 8
      Comm_resp[8] = Voltage % RESOLUTION;            // 9
      Comm_resp[9] = int(Distance / RESOLUTION);      // 10
      Comm_resp[10] = Distance % RESOLUTION;          // 11
      Comm_resp[11] = 0;                              // 12
      Comm_resp[12] = 0;                              // 13
      Comm_resp[13] = Required_Rpm_tmp[RIGHT];        // 14
      Comm_resp[14] = Required_Rpm_tmp[LEFT];         // 15
      Comm_resp[15] = 255;                            // 16

      int i = 1;
      int xchr = 0;
      Serial.write(Comm_resp[0]);
      while ( i < 15 ) {
        xchr = Comm_resp[i];
        if ( xchr == 17 ) xchr = 252;
        else if ( xchr == 19 ) xchr = 253;
        Serial.write(xchr);
        i ++;
      }
      Serial.write(Comm_resp[15]);
    }
//    else if (Debug == true){
//      Serial.println("DebugStart...........");
//      Serial.print("millis()=");
//      Serial.println(millis());
//      Serial.print("micros()=");
//      Serial.println(micros());
//      Serial.print("Last_communication_time=");
//      Serial.println(Last_communication_time);
//      for (int RL=0; RL <= 1; RL++){
//        Serial.println(String(RL) + "-Debug..............");
//        Serial.print("ChangeTime_prev=");
//        Serial.println(ChangeTime_prev[RL]);
//        Serial.print("Required_Rpm[=");
//        Serial.println(Required_Rpm[RL]);
//        Serial.print("Pwr=");
//        Serial.println(Pwr[RL]);
//        Serial.print("Rpm=");
//        Serial.println(Rpm[RL]);
//      }
//      Serial.println("DebugEnd.............");
//    }
 }

