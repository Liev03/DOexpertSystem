from flask import Flask, request, jsonify
from flask_cors import CORS
from experta import KnowledgeEngine, Rule, Fact, P

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

class OxygenPredictor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.most_relevant_warning = None
        self.most_relevant_recommendation = None
        self.relevant_issues = []  # Stores detected issues

    def add_issue(self, warning, recommendation, severity, deviation):
        """
        Adds an issue and ensures only the most critical one is returned.
        - severity: Importance of the issue (higher = more serious).
        - deviation: How far the value is from the ideal range (higher = worse).
        """
        self.relevant_issues.append({
            "warning": warning,
            "recommendation": recommendation,
            "severity": severity,
            "deviation": deviation
        })

    def finalize_decision(self):
        """Selects the most relevant issue based on severity & deviation."""
        if self.relevant_issues:
            self.relevant_issues.sort(key=lambda x: (x["severity"], x["deviation"]), reverse=True)
            best_issue = self.relevant_issues[0]
            self.most_relevant_warning = best_issue["warning"]
            self.most_relevant_recommendation = best_issue["recommendation"]

    # === Oxygen Rules ===
    @Rule(Fact(dissolved_oxygen=P(lambda x: x < 2.5)))
    def dangerously_low_oxygen(self):
        self.add_issue(
            "⚠️ Dangerously low oxygen! Fish may suffocate.",
            "Immediately activate aerators and consider partial water replacement.",
            severity=4, deviation=2.5 - x
        )

    @Rule(Fact(dissolved_oxygen=P(lambda x: 2.5 <= x < 4)))
    def low_oxygen(self):
        self.add_issue(
            "📉 Oxygen is below safe levels. Fish may be stressed.",
            "Increase aeration and reduce feeding to prevent oxygen depletion.",
            severity=3, deviation=4 - x
        )

    @Rule(Fact(dissolved_oxygen=P(lambda x: 4 <= x < 6)))
    def slightly_low_oxygen(self):
        self.add_issue(
            "🔍 Oxygen is slightly lower than ideal.",
            "Monitor closely and ensure aeration is functioning properly.",
            severity=2, deviation=6 - x
        )

    @Rule(Fact(dissolved_oxygen=P(lambda x: x > 9)))
    def excessive_oxygen(self):
        self.add_issue(
            "🌊 Excessive oxygen levels detected! Risk of gas bubble disease.",
            "Reduce aeration and avoid sudden environmental changes.",
            severity=2, deviation=x - 9
        )

    # === Temperature Rules ===
    @Rule(Fact(temperature=P(lambda x: x < 18)))
    def dangerously_cold_water(self):
        self.add_issue(
            "❄️ Water is too cold! Fish activity and immune response may drop.",
            "Gradually increase water temperature using controlled heating.",
            severity=4, deviation=18 - x
        )

    @Rule(Fact(temperature=P(lambda x: 18 <= x < 22)))
    def cold_water(self):
        self.add_issue(
            "⚠️ Water is colder than optimal. Fish metabolism slows.",
            "Adjust feeding and aeration to accommodate colder conditions.",
            severity=2, deviation=22 - x
        )

    @Rule(Fact(temperature=P(lambda x: x > 32)))
    def dangerously_hot_water(self):
        self.add_issue(
            "🔥 Extreme water temperature detected! Oxygen depletion risk.",
            "Shade the pond, increase aeration, and consider partial water change.",
            severity=4, deviation=x - 32
        )

    @Rule(Fact(temperature=P(lambda x: 28 <= x <= 32)))
    def high_temperature(self):
        self.add_issue(
            "📈 High water temperature detected.",
            "Increase aeration and monitor fish for signs of stress.",
            severity=2, deviation=x - 28
        )

    # === Ammonia Rules ===
    @Rule(Fact(ammonia=P(lambda x: x > 2)))
    def toxic_ammonia(self):
        self.add_issue(
            "☠️ Toxic ammonia levels detected! Fish are at high risk.",
            "Perform an immediate water change and check filtration.",
            severity=5, deviation=x - 2
        )

    @Rule(Fact(ammonia=P(lambda x: 0.5 < x <= 2)))
    def elevated_ammonia(self):
        self.add_issue(
            "⚠️ Elevated ammonia levels. Prolonged exposure is harmful.",
            "Reduce feeding, increase aeration, and improve biofiltration.",
            severity=3, deviation=x - 0.5
        )

    # === pH Rules ===
    @Rule(Fact(pH=P(lambda x: x < 5.5)))
    def dangerously_low_pH(self):
        self.add_issue(
            "🔴 Extremely acidic water! Risk of fish stress and disease.",
            "Gradually add pH buffers like crushed coral or baking soda.",
            severity=4, deviation=5.5 - x
        )

    @Rule(Fact(pH=P(lambda x: 5.5 <= x < 6.5)))
    def low_pH(self):
        self.add_issue(
            "⚠️ Low pH detected. Water is slightly acidic.",
            "Monitor closely and adjust with natural buffers.",
            severity=2, deviation=6.5 - x
        )

    @Rule(Fact(pH=P(lambda x: x > 9)))
    def dangerously_high_pH(self):
        self.add_issue(
            "🟢 pH is dangerously high! Risk of fish stress and chemical toxicity.",
            "Use natural pH-lowering methods like peat moss.",
            severity=4, deviation=x - 9
        )

    @Rule(Fact(pH=P(lambda x: 8.5 < x <= 9)))
    def high_pH(self):
        self.add_issue(
            "⚠️ Elevated pH detected. Alkalinity may affect fish health.",
            "Introduce gradual pH-lowering treatments.",
            severity=2, deviation=x - 8.5
        )

    # === Salinity Rules ===
    @Rule(Fact(salinity=P(lambda x: x > 12)))
    def extreme_salinity(self):
        self.add_issue(
            "⚠️ Salinity is extremely high! Risk of dehydration for freshwater species.",
            "Dilute with fresh water gradually to avoid shock.",
            severity=4, deviation=x - 12
        )

    @Rule(Fact(salinity=P(lambda x: 10 <= x <= 12)))
    def high_salinity(self):
        self.add_issue(
            "⚠️ Elevated salinity detected.",
            "Monitor fish behavior and adjust water balance if needed.",
            severity=2, deviation=x - 10
        )

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    predictor = OxygenPredictor()
    predictor.reset()
    predictor.declare(Fact(**data))
    predictor.run()
    predictor.finalize_decision()  # Pick the most critical issue

    result = {
        "warnings": [predictor.most_relevant_warning] if predictor.most_relevant_warning else [],
        "recommendations": [predictor.most_relevant_recommendation] if predictor.most_relevant_recommendation else []
    }
    return jsonify(result)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
