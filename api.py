from flask import Flask, jsonify
from flask_cors import CORS
from experta import *
import mysql.connector
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow all origins

class WaterQuality(Fact):
    """Fact model for water quality conditions"""
    temperature = Field(float)
    pH = Field(float)
    salinity = Field(float)
    ammonia = Field(float)
    dissolved_oxygen = Field(float)
    time_of_day = Field(str)

class OxygenPredictor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.warnings = []
        self.recommendations = []

    def add_warning(self, message):
        """Store warning messages"""
        self.warnings.append(message)

    def add_recommendation(self, message):
        """Store recommendation messages"""
        self.recommendations.append(message)

    # AI Rules as you defined
    @Rule(WaterQuality(temperature=P(lambda t: t > 30), dissolved_oxygen=P(lambda o: o < 4)))
    def critical_oxygen_drop(self):
        self.add_warning("🚨 High temperature detected! Oxygen depletion is critical.")
        self.add_recommendation("Increase aeration and consider shading.")

    @Rule(WaterQuality(temperature=P(lambda t: t > 35), dissolved_oxygen=P(lambda o: o < 3)))
    def extreme_heat_danger(self):
        self.add_warning("🔥 Extreme heat detected! Oxygen levels critically low.")
        self.add_recommendation("Increase aeration, perform water exchange, and reduce feeding.")

    @Rule(WaterQuality(temperature=P(lambda t: t < 15)))
    def low_temp_slow_metabolism(self):
        self.add_warning("⚠️ Low temperature detected! Fish metabolism slows down.")
        self.add_recommendation("Adjust feeding schedules and monitor fish activity.")

    @Rule(WaterQuality(salinity=P(lambda s: s > 40)))
    def high_salinity_risk(self):
        self.add_warning("⚠️ High salinity detected! Oxygen solubility decreases, increasing fish stress.")
        self.add_recommendation("Perform partial freshwater exchange.")

    @Rule(WaterQuality(temperature=P(lambda t: t > 30), salinity=P(lambda s: s > 35)))
    def high_temp_high_salinity(self):
        self.add_warning("🚨 High temperature & salinity detected! Oxygen loss is accelerated.")
        self.add_recommendation("Increase aeration and add freshwater.")

    @Rule(WaterQuality(ammonia=P(lambda a: a > 0.5), dissolved_oxygen=P(lambda o: o < 4)))
    def ammonia_stress_oxygen_drop(self):
        self.add_warning("🚨 High ammonia & low oxygen detected! Fish stress is critical.")
        self.add_recommendation("Perform water exchange and check for overfeeding.")

    @Rule(WaterQuality(ammonia=P(lambda a: a > 1)))
    def severe_ammonia_toxicity(self):
        self.add_warning("⚠️ Severe ammonia toxicity detected! Oxygen demand increased.")
        self.add_recommendation("Improve filtration, remove organic waste, and reduce stocking density.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 5)))
    def low_oxygen_warning(self):
        self.add_warning("🚨 Low oxygen detected! Aeration needed.")
        self.add_recommendation("Increase aeration, especially in warm weather.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 3)))
    def critical_low_oxygen(self):
        self.add_warning("🚨 Critically low oxygen! High risk of fish mortality.")
        self.add_recommendation("Emergency aeration required.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o > 10)))
    def high_oxygen_saturation(self):
        self.add_warning("⚠️ Excess oxygen detected! Risk of gas bubble disease.")
        self.add_recommendation("Reduce aeration and monitor fish behavior.")

    @Rule(WaterQuality(time_of_day="night", dissolved_oxygen=P(lambda o: o < 5)))
    def night_oxygen_depletion(self):
        self.add_warning("⚠️ Night-time oxygen drop detected! Algae respiration may be depleting oxygen.")
        self.add_recommendation("Ensure aerators are running at night.")

    @Rule(WaterQuality(time_of_day="night", dissolved_oxygen=P(lambda o: o < 4), ammonia=P(lambda a: a > 0.7)))
    def night_algae_ammonia_risk(self):
        self.add_warning("🚨 Night-time oxygen depletion & ammonia toxicity detected! Immediate action required.")
        self.add_recommendation("Increase nighttime aeration and reduce organic waste.")

# Function to fetch the latest sensor data from the database
def fetch_sensor_data():
    # Database connection
    conn = mysql.connector.connect(
        host='localhost',
        user='u790191610_bryan',
        password='Baklasiliam123',
        database='u790191610_aqualensedb'
    )

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY LAST_SAVED DESC LIMIT 1")
    row = cursor.fetchone()
    
    # Extract the latest data from the row
    if row:
        temperature = float(row[3])  # TEMPERATURE column
        ph_level = float(row[2])  # PH_LEVEL column
        ammonia_level = float(row[4])  # AMMONIA_LEVEL column
        dissolved_oxygen = float(row[5])  # DO_LEVEL column
        salinity_level = float(row[6])  # SALINITY_LEVEL column
        last_saved = row[7]  # LAST_SAVED column

        # Determine time of day based on last saved timestamp
        time_of_day = determine_time_of_day(last_saved)

        # Return the processed data
        return {
            "temperature": temperature,
            "pH": ph_level,
            "salinity": salinity_level,
            "ammonia": ammonia_level,
            "dissolved_oxygen": dissolved_oxygen,
            "time_of_day": time_of_day
        }

    cursor.close()
    conn.close()
    return None

# Function to determine whether it's day or night
def determine_time_of_day(last_saved):
    last_saved_time = datetime.strptime(last_saved, '%Y-%m-%d %H:%M:%S')
    if 6 <= last_saved_time.hour < 18:
        return "day"
    else:
        return "night"

@app.route('/predict', methods=['GET'])
def predict():
    # Fetch the latest sensor data from the database
    sensor_data = fetch_sensor_data()
    
    if sensor_data:
        # Initialize the AI engine and process the data
        engine = OxygenPredictor()
        engine.reset()
        engine.declare(WaterQuality(**sensor_data))
        engine.run()

        # Return AI warnings and recommendations
        return jsonify({
            "warnings": engine.warnings,
            "recommendations": engine.recommendations
        })
    else:
        return jsonify({"error": "No data found in the database."}), 400

if __name__ == '__main__':
    app.run(debug=True)
