# Changelog All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## Added
- Freerun throttle:  In freerun mode, the GUI sensor reading will update after 0.1 seconds or after one measurement, whichever is longer
- Sensors busy states are polled more frequently (10 --> 100 Hz), which can significantly speed up acquisitions with fast measurements

## Fixed
- hard crashes caused by multithread access to data, data access now regulated by explicit lock

# [2020.12.1]

## Fixed
- offsets are stored and loaded properly, weird walking off behavior at startup fixed
- offsets set to zero when hardware is zeroed

## [2020.12.0]

### Added
- initial release
- previously released under the name "PyCMDS" via github, never packaged.

[Unreleased]: https://github.com/wright-group/yaqc-cmds/compare/2020.12.1...master
[2020.12.1]: https://github.com/wright-group/yaqc-cmds/compare/2020.12.0...2020.12.1
[2020.12.0]: https://github.com/wright-group/yaqc-cmds/releases/tag/2020.12.0
