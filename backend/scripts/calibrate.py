"""Calibre le moteur actuariel sur le portefeuille simulé et affiche les
résumés des modèles GLM ainsi qu'un exemple de tarification.

Usage: python -m scripts.calibrate (depuis afririsk-auto-rca/backend/)
"""
from app.actuarial.data_simulation import generate_portfolio
from app.actuarial.pricing import ActuarialEngine


def main() -> None:
    portfolio = generate_portfolio()
    engine = ActuarialEngine()
    engine.fit(portfolio)

    print("=" * 70)
    print("Modèle de fréquence (GLM Poisson)")
    print("=" * 70)
    print(engine.freq_model.summary())

    print("\n" + "=" * 70)
    print("Modèle de sévérité (GLM Gamma)")
    print("=" * 70)
    print(engine.sev_model.summary())

    exemple = {
        "age_conducteur": 22,
        "anciennete_permis": 3,
        "usage": "professionnel",
        "zone": "bangui",
        "puissance_cv": 10,
        "valeur_vehicule_fcfa": 12_000_000,
        "garantie": "tous_risques",
        "nb_sinistres_anterieurs": 2,
    }
    resultat = engine.price(exemple)

    print("\n" + "=" * 70)
    print("Exemple de tarification")
    print("=" * 70)
    for champ, valeur in resultat.__dict__.items():
        print(f"{champ:35s}: {valeur}")


if __name__ == "__main__":
    main()
