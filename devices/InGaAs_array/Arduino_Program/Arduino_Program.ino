/*  
 A program to continuously read from a photodiode array and send the results over
 USB. It is meant to interface with the corresponding LabView vi.

 Written by: Matthew Rowley
 May 28, 2014
 
 Edited by Blaise Thompson August 2014
*/
#include <Wire.h>
//#include <avr/wdt.h> // include watchdog header
unsigned int c_reg = 0;
const int led_pin = 13; // to give user feedback (is it looping?)
const int sleep_pin = 16; // A.13 Sleeps both the AD7892 and the DS1077 (sleep is currently not implemented)
const int reset_pulse_pin = 17; // A.12
const int AD7892_cs_pin = 18; // A.11 This is essentially a cs pin, but the pin labeled CS is only used in parallel mode
const int AD7892_eoc_pin = 25; // D.0
const int gain_pin = 19;
const int data_bus[]={
  33,34,35,36,37,38,39,40,41,46,45,44};// {C.1,C.2,C.3,C.4,C.5,C.6,C.7,C.8,C.9,C.17,C.18,C.19}
word pixel_data[256]={5}; // A default array of 5s indicates that the data was never overwritten
volatile boolean pixel_ready = false;
const int ds_address = 0xB0 >> 1; // DS1077 default address from its datasheet is 10110000,
                                  // or B0 but the wire library drops the read/write bit 
                                  // and instead uses different read/write functions.
int reset_time = 1000;
int runs_summed = 1;
boolean running = false; // running ensures that the acquisitions won't begin until communication with labView is initiated
String reset_string = "0000200";
String runs_string = "003";

void setup(){
  REG_WDT_MR = 0x0fff2fff; // enable watchdog timer at maximum time (16 seconds)
  pinMode(led_pin, OUTPUT);
  pinMode(sleep_pin, OUTPUT);
  pinMode(reset_pulse_pin, OUTPUT);
  pinMode(AD7892_cs_pin, OUTPUT);
  pinMode(AD7892_eoc_pin,INPUT);
  pinMode(gain_pin,OUTPUT);
  for (int i =0 ; i<12 ; i++) pinMode(data_bus[i],INPUT); 
  digitalWrite(sleep_pin,LOW); // Ensure that the oscillator is awake
  Wire.begin();
  SerialUSB.begin(57600);
  attachInterrupt(AD7892_eoc_pin,trigger,FALLING);
// initializeDS1077(105);  // This method is called only in debugging situations 
  SerialUSB.println("ready  from startup");
  delay(100);
}

void loop(){
  WDT_Restart(WDT); // reset watchdog timer... start counting down
  digitalWrite(led_pin, LOW);
  if(SerialUSB.available()>0){ //listen for serial input
    char code = SerialUSB.read();
    if(code=='C') setClock(SerialUSB.parseInt());// 'C' signals a frequency to set 
    else if(code=='A') setAcquireParameters(SerialUSB.parseInt(),1);// 'A' signals a change in acquisition parameters
    else if(code=='G') setGain(SerialUSB.parseInt());// 'G' signals a gain change
    else if(code=='S') acquire();
    else if(code=='T') test_wd(); // dummy function to test the watchdog timer functionality
    SerialUSB.println("ready");
  }
  //while(SerialUSB.available()>0) SerialUSB.read();// Flush the Serial rx buffer just in case errant characters were sent
  digitalWrite(led_pin, HIGH);
  delay(25); // Don't loop like crazy if acquisitions haven't started yet
}

void setAcquireParameters(int integration_time, int runs){
  //SerialUSB.print(integration_time);
  reset_time = integration_time;
  runs_summed = runs;
  //reset_string = String(reset_time);
  //if(reset_time<1000000) reset_string = "0" + reset_string;
  //if(reset_time<100000) reset_string = "0" + reset_string;
  //if(reset_time<10000) reset_string = "0" + reset_string;
  //if(reset_time<1000) reset_string = "0" + reset_string;
  //if(reset_time<100) reset_string = "0" + reset_string;
  //if(reset_time<10) reset_string = "0" + reset_string;
  //runs_string = String(runs_summed);
  //if(runs_summed<100) runs_string = "0" + runs_string;
  //if(runs_summed<10) runs_string = "0" + runs_string;
  SerialUSB.flush();
  delay(100);
}

void setGain(int gain){
  //SerialUSB.println(gain);
  digitalWrite(gain_pin, gain);
  SerialUSB.flush();
}

void acquire(){
  for (int i=0;i<=255;i++){ // Clear the pixeldata array
    pixel_data[i]=0;
  }
  for (int r=0;r<runs_summed;r++){
    REG_PIOA_ODSR |= 1<<12; // Pulls the reset pulse High to begin integration
    delayMicroseconds(reset_time);
    REG_PIOA_ODSR &= ~(1<<12); // Pulls the reset pulse Low

    for(int i =0;i<=255;i++){ // Gather data from the Photodiode Array
      pixel_ready=false;
      while(!pixel_ready){;}   // Wait until the eoc interrupt from the ADC
      REG_PIOA_ODSR &= ~(1<<11); // pull the cs and rd pins low to enable parallel outputs on ADC.
      c_reg=REG_PIOC_PDSR;
      pixel_data[i]+= ((c_reg>>8)&0B111000000000)|((c_reg>>1)&0B111111111); // This shifts the bits around since the data
                                                                            // is not contiguous on the c register
      REG_PIOA_ODSR |= 1<<11; // Pull the cs and rd pins high again. 
    }
    delayMicroseconds(10);
  }
  for (int i=0;i<256;i++){
    word high_byte = pixel_data[i]>>8;
    // The most significant 8 bits. I swapped two wires on the physical circuit, so here we swap them back in software
    SerialUSB.write((high_byte & 0B1000)>>2 | (high_byte & 0B0010)<<2 | (high_byte & 0B101)); 
    SerialUSB.write(pixel_data[i]); // The least significant 8 bits
    //SerialUSB.write((pixel_data[i] && 0B000000111111)<<1); // The least significant 6 bits
  }
  //SerialUSB.write(0B00000001); // This is the end of communication character
  //SerialUSB.write(0x7f);
  SerialUSB.flush(); // This importantly prevents the USB buffer from overflowing in case the LabView vi is running slowly
}

void trigger(){
  pixel_ready=true;
}

void initializeDS1077(int kHz){ // This sets the BUS and MUX registers to their appropriate values
  delay(100);
  Wire.beginTransmission(ds_address);
  Wire.write(B00001101); // 00001101-This writes to the BUS register
  Wire.write(B00001000); // marks the address as 000 and defers writing to EEPROM
  Wire.endTransmission();
  delay(100);
  Wire.beginTransmission(ds_address);
  Wire.write(B00000010); // 00000010-This writes to the MUX register
  Wire.write(B00000110); // Sets CTRL0 as powerdown (on high), disables Out0
  Wire.write(B10000000); // Sets prescaler1 to 2
  Wire.endTransmission();
  delay(100);
  setClock(kHz); 
}

void setClock(int kHz){ // This changes the DS1077 out1 frequency
  kHz = constrain(kHz,100,120);
  byte high_byte;
  byte low_byte;
  long divisor;
  // Find the appropriate DIV register bits
  divisor = 133333 / (2*kHz);
  high_byte = divisor >> 2;
  low_byte = divisor << 8;
  Wire.beginTransmission(ds_address);
  Wire.write(B00000001); // 00000001-This writes to the DIV register
  Wire.write(high_byte);
  Wire.write(low_byte);
  Wire.endTransmission();
  delay(100);
  Wire.beginTransmission(ds_address);
  Wire.write(B00111111); // 00111111-This writes all changes to the EEPROM
  Wire.endTransmission();
  SerialUSB.flush();
}

void test_wd(){
  SerialUSB.println("test_wd");
  for(int i =0;i<=60;i++){
    delay(1000);
    SerialUSB.println(i+1);
  }  
}
