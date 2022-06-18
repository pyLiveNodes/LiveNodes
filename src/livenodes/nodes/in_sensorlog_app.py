import numpy as np
import time
import socket


from livenodes.core.sender import Sender

from . import local_registry


# TODO: consider also providing a udp version of this...
@local_registry.register
class In_sensorlog_app(Sender):
    """

    """

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

    sample_rate = 100

    channels_in = []
    channels_out = [
        'Data', 'Meta', 'Channel Names'
    ]

    category = "Data Source"
    description = ""

    example_init = {
        "name": "SensorLog App Input",
    }

    def _run(self):
        """
        Streams the data and calls frame callbacks for each frame.
        """
        self._emit_data({'sample_rate': self.sample_rate}, channel="Meta")
        self._emit_data(self.channels, channel="Channel Names")
