# TfL Bus Route Optimization Project

Automated data collection for London bus route analysis and optimization.

## Data Collection Status
- **Routes monitored**: 25, 73, 149
- **Collection frequency**: Every 10 minutes (144 times/day)
- **Data types**: 
  - Bus arrivals & timing
  - Road disruptions
  - Weather conditions (temperature, rain, wind)
  - Stop locations

## Data Sources
- **TfL Unified API**: Bus arrivals, disruptions, routes
- **Open-Meteo API**: Weather data (free, no key required)

## Data Files
- `data/stops/` - Static route and stop information
- `data/arrivals/` - Bus arrival predictions (time-stamped)
- `data/disruptions/` - Road disruptions affecting routes
- `data/weather/` - Weather conditions (temp, rain, wind)

## Project Goal
Identify inefficient bus route segments and propose data-driven rerouting solutions to reduce journey times, analyzing the impact of weather and road conditions on bus performance.

## Analysis Questions
1. Which route segments are consistently delayed?
2. How does weather affect bus journey times?
3. What alternative routes could reduce delays?
4. When do specific routes need frequency adjustments?

---
*Data collected automatically via GitHub Actions*
*Weather data: Open-Meteo (CC BY 4.0 License)*
*Transport data: TfL Open Data*