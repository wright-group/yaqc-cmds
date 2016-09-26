//NDs_control arduino sketch
//blaise thompson - blaise@untzag.com
//last updated may 2014

//this is 'customized' to work with the electronics version 1
//note that motor2 is backwards...

//--------------------------------------------------------------------------------------------

//define & declare needed variables, arrays, etc.
int motor = 0;
int steps = 0;
char code = 'M';
int current_interrupt = 0;
byte busy = 1;
byte waiting = 2;

//stepper motor
int pin_A1 = 2;
int pin_A2 = 3;
int pin_B1 = 4;
int pin_B2 = 5;
#include <Stepper.h>
#define STEPS 20
Stepper step_backward(STEPS, pin_A1, pin_A2, pin_B1, pin_B2);
Stepper step_forward(STEPS, pin_B2, pin_B1, pin_A2, pin_A1);

//channels
int on_board_led = 13;
int motor_1 = 8;
int motor_2 = 10;
int motor_3 = 12;
int motor_1_interrupt = 7;
int motor_2_interrupt = 9;
int motor_3_interrupt = 11;

//--------------------------------------------------------------------------------------------
//setup

void setup(){
  //initiate pins
  pinMode(on_board_led, OUTPUT);
  pinMode(motor_1, OUTPUT);
  pinMode(motor_2, OUTPUT);
  pinMode(motor_3, OUTPUT);
  digitalWrite(motor_1, LOW);
  digitalWrite(motor_2, LOW);
  digitalWrite(motor_3, LOW);
  pinMode(pin_A1, OUTPUT);
  pinMode(pin_A2, OUTPUT);
  pinMode(pin_B1, OUTPUT);
  pinMode(pin_B2, OUTPUT);
  digitalWrite(pin_A1, LOW);
  digitalWrite(pin_A2, LOW);
  digitalWrite(pin_B1, LOW);
  digitalWrite(pin_B2, LOW);
  pinMode(motor_1_interrupt, INPUT);
  pinMode(motor_2_interrupt, INPUT);
  pinMode(motor_3_interrupt, INPUT);
  //initiate stepper motor
  step_forward.setSpeed(100);
  step_backward.setSpeed(100);
  //initiate serial
  Serial.begin(57600);
  while (!Serial) ; //wait for port to connect
  Serial.print("ready");
}

//--------------------------------------------------------------------------------------------
//loop

void loop(){
  
  //listen for serial input
  if (Serial.available()>0){
    Serial.println("busy");
    code = Serial.read();
    if (code == 'M') moveMotor(Serial.parseInt(), Serial.parseInt()); 
    else if(code == 'H') homeMotor(Serial.parseInt());
    else delay(100);
    Serial.flush();
    Serial.println("ready");}
    
  //delay and loop
  digitalWrite(on_board_led, HIGH);
  delay(5);
  digitalWrite(on_board_led, LOW);
  Serial.flush();}

//--------------------------------------------------------------------------------------------
//move motor function

void moveMotor(int steps, int motor) {
  
  //activate appropriate motor
  if (motor == 1) digitalWrite(motor_1, HIGH);
  else if (motor == 2) digitalWrite(motor_2, HIGH), steps = -steps;
  else if (motor == 3) digitalWrite(motor_3, HIGH);
  else delay(100);
  
  //move motor
  if (steps >= 0) {
    step_forward.step(steps);}
  else if (steps <= 0) {
    steps = -steps;
    step_backward.step(steps);}
  else delay(100);
      
  //write all pins LOW after movement done
  digitalWrite(pin_A1, LOW);
  digitalWrite(pin_A2, LOW);
  digitalWrite(pin_B1, LOW);
  digitalWrite(pin_B2, LOW);  
  digitalWrite(motor_1, LOW);
  digitalWrite(motor_2, LOW);
  digitalWrite(motor_3, LOW);}
    
//--------------------------------------------------------------------------------------------
//home motor funciton

void homeMotor(int motor){
  
  //activate appropriate motor
  if (motor == 1) {
    digitalWrite(motor_1, HIGH);
    current_interrupt = motor_1_interrupt;}
  else if (motor == 2) {
    digitalWrite(motor_2, HIGH);
    current_interrupt = motor_2_interrupt;}
  else if (motor == 3) {
    digitalWrite(motor_3, HIGH);
    current_interrupt = motor_3_interrupt;}
  else delay(100);
  
  //move motor until interrupt trips
  while (digitalRead(current_interrupt) == LOW){
    if (motor == 2) {step_forward.step(1);}
    else step_backward.step(1);}
    
  //write all pins LOW after movement done
  digitalWrite(pin_A1, LOW);
  digitalWrite(pin_A2, LOW);
  digitalWrite(pin_B1, LOW);
  digitalWrite(pin_B2, LOW);  
  digitalWrite(motor_1, LOW);
  digitalWrite(motor_2, LOW);
  digitalWrite(motor_3, LOW);}
