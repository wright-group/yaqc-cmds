

// DynacronDelay_control Arduino sketch
// Darien Morrow - darienmorrow@gmail.com - dmorrow3@wisc.edu
// first created January 1, 2016
// last updated January 7, 2016

//--------------------------------------------------------------------------------------------

// Define and declare needed variables.
long position_current = 0; // This is the current position of the stage in units of steps.
long position_saved = 0; // This is the EEPROM saved position of the stage in units of steps.

long updates = 0; // This long controls if the user will get movement updates as the stage moves. 0 = off, 1+ = on and print every that many steps.

float inchsperstep = 0.000033334; // This is how many inches the stage moves for each motor step.

// Define and declare needed read & write channels.
int on_board_led = 13;
int clock_m = 22;
int direction_m = 23;
int limit_ccw = 24;
int limit_cw = 25;

#include <EEPROM.h>

//--------------------------------------------------------------------------------------------
// Setup

void setup() {
  // Initiate pins and write outputs to logic LOW.
  pinMode(on_board_led, OUTPUT);
  pinMode(clock_m, OUTPUT);
  pinMode(direction_m, OUTPUT); // The logic potential of this output controls which direction the stage moves.
  digitalWrite(on_board_led, LOW);
  digitalWrite(clock_m, LOW);
  digitalWrite(direction_m, LOW);
  pinMode(limit_ccw, INPUT);
  pinMode(limit_cw, INPUT);
  
  // Startup settings update.
  EEPROMLet(); // Sets the current position to the last saved position.
  
  // Initiate serial port communcation.
  Serial.begin(57600);
  while (!Serial) ; // Wait for port to connect.
  Serial.println("ready");
}

//--------------------------------------------------------------------------------------------
// Loop

void loop() {

  // Listen for serial input.
  if (Serial.available() > 0) {
    Serial.println("busy");
    char code = Serial.read();
    // Complete tasks given various serial inputs.
    if (code == 'M') MoveStage(Serial.parseFloat());
    else if (code == 'A') AchieveStagePosition(Serial.parseFloat());
    else if (code == 'T') TranslateStage((long)Serial.parseInt());
    else if (code == 'K') TranslateStageNoQuestionsAsked((long)Serial.parseInt());
    else if (code == 'H') HomeStage();
    
    else if (code == 'P') Serial.println(position_current); // Prints current stage position in units of steps.
    else if (code == 'G') GetStagePosition();
    else if (code == 'U') updates = Serial.parseInt(); // Changes the user status update settings.
    
    else if (code == 'S') EEPROMWritelong(0, position_current); // Saves the current position (in steps) to EEPROM.
    else if (code == 'R') Serial.println(EEPROMReadlong(0)); // Reads and prints the EEPROM position (in steps).
    else if (code == 'Q') EEPROMQuery(); // Reads and prints the EEPROM position (in mm).
    else if (code == 'L') EEPROMLet(); // Tells the Arduino that the current stage postion is the saved EEPROM position. 
    
    else delay(100);
    Serial.flush();
    Serial.println("ready");
  }

  //delay and loop
  delay(5);
  Serial.flush();

}


//--------------------------------------------------------------------------------------------
// Move stage function

// This function moves the stage the specified amount (in mm) in relative terms.
// A postive float input entails that the stage will move towards the far limit (CW).
// A negative float input entails that the stage will move towards the near limit (CCW).


void MoveStage(float distance) {

  digitalWrite(on_board_led, HIGH);
  long stepstaken = 0;
  int limitswitch = 0; 
  
  // Tell the motor what direction to move and what limit is in that direction.
  long sign = 0;
  if (distance >= 0.0) {
    sign = 1;
    digitalWrite(direction_m, HIGH);
    limitswitch = limit_cw; 
  }
  else if (distance < 0.0) {
    sign = -1;
    digitalWrite(direction_m, LOW);
    limitswitch = limit_ccw; 
  }

  

  // Calculate how much to move the stage.
  // This truncates to an integer number of steps. 1 micron is close to the smallest possible distance.
  long steps = (long)(distance / 25.4 / inchsperstep); 

  // Move the stage.
  // The boolean constraints on the for loop ensure that the motor does not continue to get a signal if it is at its limit. 
  for (long x = 0; x < abs(steps) && digitalRead(limitswitch) == HIGH ; x++) {
    digitalWrite(clock_m, HIGH);
    delayMicroseconds(167);
    digitalWrite(clock_m, LOW);
    delayMicroseconds(167);
    // Provide user readable updates.
    if (updates != 0) {
       if ((x + 1)%updates == 0) {
        float position_current_mm = (float)(position_current + x + 1 ) * 25.4 * inchsperstep;
        Serial.print("Current position of stage ");
        Serial.println(position_current_mm, DEC);
       }
    }
    stepstaken = x + 1;   
  }

  // Update the global tracker of stage position as well as the user about the current position of the stage.
  position_current = position_current + (sign * stepstaken);
  float stepstaken_mm = (float)(sign * stepstaken) * 25.4 * inchsperstep;
  float position_current_mm = (float)(position_current) * 25.4 * inchsperstep;
  Serial.print("Moved the stage ");
  Serial.println(stepstaken_mm, DEC);  
  Serial.print("Current position of stage ");
  Serial.println(position_current_mm, DEC);
  
  digitalWrite(on_board_led, LOW);
}

//--------------------------------------------------------------------------------------------
// Achieve stage position function

// This function moves the stage to the specified, absolute position (in mm).

void AchieveStagePosition(float position_desired_mm) {

  digitalWrite(on_board_led, HIGH);
  long stepstaken = 0;
  int limitswitch = 0;
  
  // Calculate where to move the stage.
  // This truncates to an integer number of steps. 1 micron is close to the smallest possible distance.
  long position_desired_steps = (long)(position_desired_mm / 25.4 / inchsperstep);  
  long steps = position_desired_steps - position_current; 

  // Tell the motor what direction to move.
  long sign = 0;
  if (steps >= 0.0) {
    sign = 1;
    digitalWrite(direction_m, HIGH);
    limitswitch = limit_cw; 
  }
  else if (steps < 0.0) {
    sign = -1;
    digitalWrite(direction_m, LOW);
    limitswitch = limit_ccw;
  }

  // Move the stage.
  // The boolean constraints on the for loop ensure that the motor does not continue to get a signal if it is at its limit. 
  for (long x = 0; x < abs(steps) && digitalRead(limitswitch) == HIGH; x++) {
    digitalWrite(clock_m, HIGH);
    delayMicroseconds(167);
    digitalWrite(clock_m, LOW);
    delayMicroseconds(167);
        // Provide user readable updates.
    if (updates != 0) {
       if ((x + 1)%updates == 0) {
        float position_current_mm = (float)(position_current + x + 1) * 25.4 * inchsperstep;
        Serial.print("Current position of stage ");
        Serial.println(position_current_mm, DEC);
       }
    }
    stepstaken = x + 1;   
  }

  // Update the global tracker of stage position as well as the user about the current position of the stage.
  position_current = position_current + (sign * stepstaken);
  float stepstaken_mm = (float)(sign * stepstaken) * 25.4 * inchsperstep;
  float position_current_mm = (float)(position_current) * 25.4 * inchsperstep;
  Serial.print("Moved the stage ");
  Serial.println(stepstaken_mm, DEC);  
  Serial.print("Current position of stage ");
  Serial.println(position_current_mm, DEC);
  
  digitalWrite(on_board_led, LOW);  
}

//--------------------------------------------------------------------------------------------
// Home stage function

// This function moves the stage to the near limit (CCW).

void HomeStage() {

  digitalWrite(on_board_led, HIGH);
  
  digitalWrite(direction_m, LOW); // Tells the motor to move stage toward the near limit.
  while (digitalRead(limit_ccw) == HIGH) {
    digitalWrite(clock_m, HIGH);
    delayMicroseconds(167);
    digitalWrite(clock_m, LOW);
    delayMicroseconds(167);
    
  }
  
  // Move one step away from near limit.
  // This step is needed because all translation functions require limit switches to be unactivated.
  // This moves the stage away from the limit switch until it is deactivated.  
  digitalWrite(direction_m, HIGH); // Tells the motor to move stage toward the far limit.
  while (digitalRead(limit_ccw) == LOW) {
    digitalWrite(clock_m, HIGH);
    delayMicroseconds(167);
    digitalWrite(clock_m, LOW);
    delayMicroseconds(167);
  }
  // Update the global tracker of stage position as well as the user about the current position of the stage.
  position_current = 0;
  Serial.println("homed");

  digitalWrite(on_board_led, LOW);  
}

//--------------------------------------------------------------------------------------------
// Get absolute stage position (in mm) function 

// This function returns the current stage position (in mm) to the user.

void GetStagePosition() {
 
  Serial.print("Current position of stage ");
  Serial.println((float)position_current * 25.4 * inchsperstep, DEC);  

}

//--------------------------------------------------------------------------------------------
// Translate stage function

// This function translates the stage a given number of steps.

void TranslateStage(long transsteps) {

  digitalWrite(on_board_led, HIGH);
  long stepstaken = 0;
  int limitswitch = 0;

  // Tell the motor what direction to move.
  long sign = 0;
  if (transsteps >= 0.0) {
    sign = 1;
    digitalWrite(direction_m, HIGH);
    limitswitch = limit_cw;
  }
  else if (transsteps < 0.0) {
    sign = -1;
    digitalWrite(direction_m, LOW);
    limitswitch = limit_ccw;
  }


  // Move the stage.
  // The boolean constraints on the for loop ensure that the motor does not continue to get a signal if it is at its limit. 
  for (long x = 0; x < abs(transsteps) && digitalRead(limitswitch) == HIGH; x++) {
    digitalWrite(clock_m, HIGH);
    delayMicroseconds(167);
    digitalWrite(clock_m, LOW);
    delayMicroseconds(167);
    // Provide user readable updates.
    if (updates != 0) {
       if ((x + 1)%updates == 0) {
        float position_current_mm = (float)(position_current + x + 1) * 25.4 * inchsperstep;
        Serial.print("Current position of stage ");
        Serial.println(position_current_mm, DEC);
       }
    }
    stepstaken = x + 1;   
  }

  // Update the global tracker of stage position as well as the user about the current position of the stage.
  position_current = position_current + (sign * stepstaken);
  float stepstaken_mm = (float)(sign * stepstaken) * 25.4 * inchsperstep;
  float position_current_mm = (float)(position_current) * 25.4 * inchsperstep;
  Serial.print("Moved the stage (in steps) ");
  Serial.println(stepstaken, DEC); 
  Serial.print("Moved the stage (in mm) ");
  Serial.println(stepstaken_mm, DEC);   
  Serial.print("Current position of stage (in steps) ");
  Serial.println(position_current, DEC);
  Serial.print("Current position of stage (in mm) ");
  Serial.println(position_current_mm, DEC);

  digitalWrite(on_board_led, LOW);
}


//--------------------------------------------------------------------------------------------
// Translate stage no questions asked function

// This function translates the stage a given number of steps.
// This function does not keep track of where the stage is.
// This function does not account for limit switches. 

void TranslateStageNoQuestionsAsked(long transsteps) {

  digitalWrite(on_board_led, HIGH);
  long stepstaken = 0;

  // Tell the motor what direction to move.
  long sign = 0;
  if (transsteps >= 0.0) {
    sign = 1;
    digitalWrite(direction_m, HIGH);
  }
  else if (transsteps < 0.0) {
    sign = -1;
    digitalWrite(direction_m, LOW);
  }


  // Move the stage.

  for (long x = 0; x < abs(transsteps); x++) {
    digitalWrite(clock_m, HIGH);
    delayMicroseconds(167);
    digitalWrite(clock_m, LOW);
    delayMicroseconds(167);
    stepstaken = x + 1;   
  }

  // Update  the user about the movement position of the stage.

  float stepstaken_mm = (float)(sign * stepstaken) * 25.4 * inchsperstep;

  Serial.print("Moved the stage (in steps) ");
  Serial.println(stepstaken, DEC); 
  Serial.print("Moved the stage (in mm) ");
  Serial.println(stepstaken_mm, DEC);   
  Serial.println("Now I don't know where I am :(.");
  Serial.println("I hope you know where I am.");
  
  digitalWrite(on_board_led, LOW);
}

//--------------------------------------------------------------------------------------------
// Needed EEPROM functions. Harvested from http://playground.arduino.cc/Code/EEPROMReadWriteLong .

// The following was written by Kevin Elsenberger.
 
//This function will write a 4 byte (32bit) long to the eeprom at the specified address to address + 3.
void EEPROMWritelong(long address, long value) {
  
      //Decomposition from a long to 4 bytes by using bitshift.
      //One = Most significant -> Four = Least significant byte
      byte four = (value & 0xFF);
      byte three = ((value >> 8) & 0xFF);
      byte two = ((value >> 16) & 0xFF);
      byte one = ((value >> 24) & 0xFF);

      //Write the 4 bytes into the eeprom memory.
      EEPROM.write(address, four);
      EEPROM.write(address + 1, three);
      EEPROM.write(address + 2, two);
      EEPROM.write(address + 3, one);

      Serial.println("EEPROM position set to position_current");
      }

long EEPROMReadlong(long address) {
      
      //Read the 4 bytes from the eeprom memory.
      long four = EEPROM.read(address);
      long three = EEPROM.read(address + 1);
      long two = EEPROM.read(address + 2);
      long one = EEPROM.read(address + 3);

      //Return the recomposed long by using bitshift.
      return ((four << 0) & 0xFF) + ((three << 8) & 0xFFFF) + ((two << 16) & 0xFFFFFF) + ((one << 24) & 0xFFFFFFFF);
      }

//--------------------------------------------------------------------------------------------
// EEPROM Querry function

// This function prints the saved EEPROM position (in mm).

void EEPROMQuery() {
 
  Serial.print("Current position of stage according to EEPROM ");
  Serial.println((float)EEPROMReadlong(0) * 25.4 * inchsperstep, DEC);  
}


//--------------------------------------------------------------------------------------------
// EEPROM Let function

// This function lets/sets position_current to be the saved EEPROM postion.

void EEPROMLet() {
  position_current = EEPROMReadlong(0); 
  Serial.println("position_current set to EEPROM position");   
}





