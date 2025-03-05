from flask import Flask, request, jsonify
from flask_cors import CORS
from experta import KnowledgeEngine, Rule, Fact, P, MATCH

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

class OxygenPredictor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.relevant_issues = []  # Stores detected issues

    def add_issue(self, warning, recommendation, severity, category):
        """
        Adds an issue while ensuring diversity in categories.
        - severity: Importance of the issue (higher = more serious).
        - category: The parameter category (e.g., oxygen, ammonia, temperature, etc.).
        """
        self.relevant_issues.append({
            "warning": warning,
            "recommendation": recommendation,
            "severity": severity,
            "category": category
        })

    def finalize_decision(self):
        """Selects the two most relevant issues from different categories based on severity."""
        if self.relevant_issues:
            self.relevant_issues.sort(key=lambda x: x["severity"], reverse=True)
            selected_issues = []
            seen_categories = set()
            
            for issue in self.relevant_issues:
                if issue["category"] not in seen_categories:
                    selected_issues.append(issue)
                    seen_categories.add(issue["category"])
                if len(selected_issues) == 2:
                    break
            
            self.most_relevant_warnings = [issue["warning"] for issue in selected_issues]
            self.most_relevant_recommendations = [issue["recommendation"] for issue in selected_issues]

    # === Oxygen Rules ===
    @Rule(Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 3)))
    def critically_low_oxygen(self, do):
        self.add_issue("⚠️ Dangerously low oxygen levels! Fish are at severe risk of suffocation.",
                       "Immediately turn on aerators or increase water circulation. Reduce feeding and check for organic waste buildup.", severity=5, category="oxygen")

    @Rule(Fact(dissolved_oxygen=MATCH.do & P(lambda x: 3 <= x < 5)))
    def low_oxygen(self, do):
        self.add_issue("📉 Low oxygen detected. Fish may show signs of stress.",
                       "Increase aeration, reduce stocking density if necessary, and monitor water temperature.", severity=3, category="oxygen")

    @Rule(Fact(dissolved_oxygen=MATCH.do & P(lambda x: x > 9)))
    def excessive_oxygen(self, do):
        self.add_issue("🌊 Excessive dissolved oxygen detected! Risk of gas bubble disease.",
                       "Reduce aeration and monitor fish behavior for signs of distress.", severity=2, category="oxygen")

    # === Temperature Rules ===
    @Rule(Fact(temperature=MATCH.temp & P(lambda x: x < 18)))
    def cold_water(self, temp):
        self.add_issue("❄️ Cold water detected! Fish metabolism slows down.",
                       "Reduce feeding and consider adding thermal insulation if necessary.", severity=2, category="temperature")

    @Rule(Fact(temperature=MATCH.temp & P(lambda x: x > 32)))
    def high_temperature(self, temp):
        self.add_issue("🔥 High water temperature detected! Oxygen levels drop significantly.",
                       "Increase aeration, provide shade, and avoid overfeeding.", severity=4, category="temperature")

    # === Ammonia Rules ===
    @Rule(Fact(ammonia=MATCH.amm & P(lambda x: x > 0.5)))
    def high_ammonia(self, amm):
        self.add_issue("☠️ High ammonia levels detected! Risk of fish poisoning.",
                       "Perform a partial water change, improve filtration, and reduce uneaten feed.", severity=5, category="ammonia")

    # === pH Rules ===
    @Rule(Fact(pH=MATCH.pH_val & P(lambda x: x < 6.5)))
    def low_pH(self, pH_val):
        self.add_issue("🔴 Low pH detected! Water is too acidic for optimal fish health.",
                       "Add crushed coral or baking soda gradually to stabilize pH.", severity=3, category="pH")

    @Rule(Fact(pH=MATCH.pH_val & P(lambda x: x > 8.5)))
    def high_pH(self, pH_val):
        self.add_issue("🟢 High pH detected! Water is too alkaline.",
                       "Use peat moss or introduce natural acids to lower pH levels.", severity=3, category="pH")

    # === Salinity Rules ===
    @Rule(Fact(salinity=MATCH.sal & P(lambda x: x > 10)))
    def high_salinity(self, sal):
        self.add_issue("⚠️ High salinity detected! May stress freshwater species.",
                       "Gradually dilute with fresh water to restore balance.", severity=2, category="salinity")

    # === Combination Rules ===
    @Rule(Fact(temperature=MATCH.temp & P(lambda x: x > 30)),
          Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 4)))
    def high_temp_low_oxygen(self, temp, do):
        self.add_issue("🔥 High temperature and low oxygen detected! Severe stress risk for fish.",
                       "Increase aeration, provide shade, and consider a water change.", severity=5, category="oxygen")

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    predictor = OxygenPredictor()
    predictor.reset()
    predictor.declare(Fact(**data))
    predictor.run()
    predictor.finalize_decision()

    result = {
        "warnings": predictor.most_relevant_warnings,
        "recommendations": predictor.most_relevant_recommendations
    }
    return jsonify(result)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
