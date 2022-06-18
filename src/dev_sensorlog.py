import socket
import sys
import time

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Started Socket')

sock.connect(("192.168.178.60", 61689))
print('Connected')

channels = [
        "loggingTime(txt)",
        "loggingSample(N)",
        "locationTimestamp_since1970(s)",
        "locationLatitude(WGS84)",
        "locationLongitude(WGS84)",
        "locationAltitude(m)",
        "locationSpeed(m/s)",
        "locationSpeedAccuracy(m/s)",
        "locationCourse(°)",
        "locationCourseAccuracy(°)",
        "locationVerticalAccuracy(m)",
        "locationHorizontalAccuracy(m)",
        "locationFloor(Z)",
        "locationHeadingTimestamp_since1970(s)",
        "locationHeadingX(µT)",
        "locationHeadingY(µT)",
        "locationHeadingZ(µT)",
        "locationTrueHeading(°)",
        "locationMagneticHeading(°)",
        "locationHeadingAccuracy(°)",
        "accelerometerTimestamp_sinceReboot(s)",
        "accelerometerAccelerationX(G)",
        "accelerometerAccelerationY(G)",
        "accelerometerAccelerationZ(G)",
        "gyroTimestamp_sinceReboot(s)",
        "gyroRotationX(rad/s)",
        "gyroRotationY(rad/s)",
        "gyroRotationZ(rad/s)",
        "magnetometerTimestamp_sinceReboot(s)",
        "magnetometerX(µT)",
        "magnetometerY(µT)",
        "magnetometerZ(µT)",
        "motionTimestamp_sinceReboot(s)",
        "motionYaw(rad)",
        "motionRoll(rad)",
        "motionPitch(rad)",
        "motionRotationRateX(rad/s)",
        "motionRotationRateY(rad/s)",
        "motionRotationRateZ(rad/s)",
        "motionUserAccelerationX(G)",
        "motionUserAccelerationY(G)",
        "motionUserAccelerationZ(G)",
        "motionAttitudeReferenceFrame(txt)",
        "motionQuaternionX(R)",
        "motionQuaternionY(R)",
        "motionQuaternionZ(R)",
        "motionQuaternionW(R)",
        "motionGravityX(G)",
        "motionGravityY(G)",
        "motionGravityZ(G)",
        "motionMagneticFieldX(µT)",
        "motionMagneticFieldY(µT)",
        "motionMagneticFieldZ(µT)",
        "motionHeading(°)",
        "motionMagneticFieldCalibrationAccuracy(Z)",
        "pedometerStartDate(txt)",
        "pedometerNumberofSteps(N)",
        "pedometerAverageActivePace(s/m)",
        "pedometerCurrentPace(s/m)",
        "pedometerCurrentCadence(steps/s)",
        "pedometerDistance(m)",
        "pedometerFloorAscended(N)",
        "pedometerFloorDescended(N)",
        "pedometerEndDate(txt)",
        "altimeterTimestamp_sinceReboot(s)",
        "altimeterReset(bool)",
        "altimeterRelativeAltitude(m)",
        "altimeterPressure(kPa)",
        "deviceID(txt)",
        "deviceOrientationTimeStamp_since1970(s)",
        "deviceOrientation(Z)",
        "avAudioRecorder_Timestamp_since1970(s)",
        "avAudioRecorderPeakPower(dB)",
        "avAudioRecorderAveragePower(dB)"
    ]

recv_data = ""
print ('Reading')
tmp = time.time()
while True:
    chunk = sock.recv(2048)
    if chunk == b'':
        break

    recv_data += chunk.decode("utf-8") 

    rows = recv_data.split('\n')
    if recv_data.endswith('\n'):
        recv_data = ''
    else:
        recv_data = rows[-1]
        rows = rows[:-1]

    for row in rows:
        print(row)

