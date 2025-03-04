from flask import Flask, request, jsonify
from flask_cors import CORS
from experta import *

app = Flask(__name__)
CORS(app)

class WaterQuality(Fact):
    """Fact model for water quality conditions"""
    temperature = Field(float)
    pH = Field(float)
    salinity = Field(float)
    ammonia = Field(float)
    dissolved_oxygen = Field(float)
    time_of_day = Field(str)  # "day" or "night"

class OxygenPredictor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.most_critical_warning = None
        self.most_critical_recommendation = None
        self.highest_priority = -1  # Track highest salience encountered

    def set_warning(self, message, priority):
        """Store the highest-priority warning only"""
        if priority > self.highest_priority:
            self.most_critical_warning = message
            self.highest_priority = priority

    def set_recommendation(self, message, priority):
        """Store the highest-priority recommendation only"""
        if priority > self.highest_priority:
            self.most_critical_recommendation = message

    # 🚨 CRITICAL WARNINGS (Highest Priority)
    @Rule(WaterQuality(temperature=P(lambda t: t > 35), dissolved_oxygen=P(lambda o: o < 3)), salience=10)
    def extreme_heat_danger(self):
        self.set_warning("🔥 Extreme heat! Fish may be gasping due to oxygen depletion.", 10)
        self.set_recommendation("Increase aeration and provide shade. Consider a partial water exchange.", 10)

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 3)), salience=9)
    def critical_low_oxygen(self):
        self.set_warning("⚠️ Critically low oxygen levels! Fish may be lethargic or surfacing.", 9)
        self.set_recommendation("Immediately activate aerators or increase water circulation.", 9)

    @Rule(WaterQuality(ammonia=P(lambda a: a > 1)), salience=8)
    def severe_ammonia_toxicity(self):
        self.set_warning("☠️ Dangerous ammonia levels! Fish gills may be inflamed.", 8)
        self.set_recommendation("Perform a 30-50% water change and check for excess waste.", 8)

    # ⚠️ MODERATE WARNINGS (Medium Priority)
    @Rule(WaterQuality(temperature=P(lambda t: t > 30), dissolved_oxygen=P(lambda o: o < 4)), salience=6)
    def critical_oxygen_drop(self):
        self.set_warning("🌡️ High temperature + low oxygen! Fish stress levels rising.", 6)
        self.set_recommendation("Increase aeration and monitor fish closely.", 6)

    @Rule(WaterQuality(ammonia=P(lambda a: a > 0.5), dissolved_oxygen=P(lambda o: o < 4)), salience=5)
    def ammonia_stress_oxygen_drop(self):
        self.set_warning("⚠️ Ammonia + low oxygen detected! Fish are at risk of suffocation.", 5)
        self.set_recommendation("Reduce feeding, add aeration, and perform a partial water change.", 5)

    # ℹ️ LOW-PRIORITY WARNINGS (Mild Concerns)
    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 5)), salience=2)
    def low_oxygen_warning(self):
        self.set_warning("📉 Oxygen is lower than ideal. Monitor fish closely.", 2)
        self.set_recommendation("Increase aeration, especially during warmer hours.", 2)

    @Rule(WaterQuality(temperature=P(lambda t: t < 15)), salience=1)
    def low_temp_slow_metabolism(self):
        self.set_warning("🥶 Cold water detected! Fish metabolism is slowing down.", 1)
        self.set_recommendation("Adjust feeding schedule and avoid sudden temperature changes.", 1)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        processed_data = {
            "temperature": float(data["temperature"]),
            "pH": float(data["pH"]),
            "salinity": float(data["salinity"]),
            "ammonia": float(data["ammonia"]),
            "dissolved_oxygen": float(data["dissolved_oxygen"]),
            "time_of_day": data["time_of_day"].lower()
        }

        if processed_data["time_of_day"] not in ["day", "night"]:
            return jsonify({"error": "Invalid time_of_day. Use 'day' or 'night'."}), 400

    except (ValueError, TypeError, KeyError):
        return jsonify({"error": "Invalid input data format"}), 400

    # Run expert system
    engine = OxygenPredictor()
    engine.reset()
    engine.declare(WaterQuality(**processed_data))
    engine.run()

    return jsonify({
        "warning": engine.most_critical_warning or "No critical issues detected.",
        "recommendation": engine.most_critical_recommendation or "No immediate action needed."
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
