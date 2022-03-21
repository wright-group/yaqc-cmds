# Changelog All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [2022.3.0]

### Fixed
- hook in signals which update the "main channel" combo box when sensors update/initialize

### Removed
- autonomic cosetting system is removed in favor of attune-delay daemon which handles SDC

## [2021.7.0]

### Fixed
- Ensure limits are computed when one bound should be inf
- Ensure float passed in `set_position_except` (rather than scalar ndarray)
- Motortune collecting tune points with discrete tunes
- Better consistency of autonomic system
- Ensure correct units used in acquisition
- axes with whitespace don't necessarily fail
- Motortune Tunepoints only calculated if the checkbox is checked
- old "identity" behavior removed which caused splitting on "F" in axis names
- Use expressions rather than names for processing of scan
- Decode when needed for axis dropdown in plot tab

### Added
- Widgets to control slit widths and mirror positions of monochromator

## [2021.3.0]

### Added
- support for sensors without `has-measure-trigger` trait
- support for sensors that implement `has-mapping` trait

### Changed
- Update for pint version of WrightTools (3.4.0)
- Use string based update of has-turret trait for spectrometers
- Add protection for DiscreteTune plotting

### Fixed
- Deprecated Qt function call

## [2021.1.1]

### Fixed
- Properly close files prior to new data file creation (fix file inconsistency)
- Do not use h5py libver="latest" (fix segfault upon copying)

## [2021.1.0]

### Added
- Freerun throttle:  In freerun mode, the GUI sensor reading will update after 0.1 seconds or after one measurement, whichever is longer
- Sensors busy states are polled more frequently (10 --> 100 Hz), which can significantly speed up acquisitions with fast measurements

### Fixed
- hard crashes caused by multithread access to data, data access now regulated by explicit lock
- freerun state is polled after an acquisition finishes
- set zero position at initialization time to ensure limits are set
- handling of zero position units to remove warning
- throttle delay poll (sleep 10 ms) during travel to decrease CPU workload

## [2020.12.1]

### Fixed
- offsets are stored and loaded properly, weird walking off behavior at startup fixed
- offsets set to zero when hardware is zeroed

## [2020.12.0]

### Added
- initial release
- previously released under the name "PyCMDS" via github, never packaged.

[Unreleased]: https://github.com/wright-group/yaqc-cmds/compare/2022.3.0...master
[2022.3.0]: https://github.com/wright-group/yaqc-cmds/compare/2021.7.0...2022.3.0
[2021.7.0]: https://github.com/wright-group/yaqc-cmds/compare/2021.3.0...2021.7.0
[2021.3.0]: https://github.com/wright-group/yaqc-cmds/compare/2021.1.1...2021.3.0
[2021.1.1]: https://github.com/wright-group/yaqc-cmds/compare/2021.1.0...2021.1.1
[2021.1.0]: https://github.com/wright-group/yaqc-cmds/compare/2020.12.1...2021.1.0
[2020.12.1]: https://github.com/wright-group/yaqc-cmds/compare/2020.12.0...2020.12.1
[2020.12.0]: https://github.com/wright-group/yaqc-cmds/releases/tag/2020.12.0
