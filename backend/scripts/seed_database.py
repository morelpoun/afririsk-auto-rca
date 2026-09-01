"""Peuple la base (clients, véhicules, polices, sinistres) avec des données
synthétiques réalistes, pour donner du contenu à GET /portfolio/kpis et à
GET /policies /claims sans dépendre d'un vrai assureur. Les primes sont
calculées avec le moteur de production ; les sinistres réalisés viennent de
la simulation (app/actuarial/data_simulation.py), ce qui donne un loss ratio
non trivial (le vécu diffère de la prime tarifée, comme dans la réalité).

Usage: cd backend && python -m scripts.seed_database [--n 500]
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta

from app.actuarial.data_simulation import generate_portfolio
from app.actuarial.pricing import ActuarialEngine
from app.database import crud
from app.database.session import SessionLocal, init_db
from app.regulatory.countries import cf as cf_rules
from app.regulatory.rules import check_minimum_tariff

VEHICLES = [
    ("Toyota", "Corolla", "berline"),
    ("Toyota", "Hilux", "pickup"),
    ("Nissan", "Note", "berline"),
    ("Toyota", "Land Cruiser", "suv"),
    ("Hyundai", "Tucson", "suv"),
    ("Kia", "Rio", "berline"),
]
CLAIM_TYPES = ["materiel", "corporel", "vol"]

MODEL_VERSION = "GLM_FREQ_SEV_V1"
COUNTRY = "CF"
PRODUCT = "AUTO_RC"
TODAY = date(2026, 9, 1)


def seed(n: int, seed_value: int = 123) -> None:
    init_db()
    cf_rules.load()

    calibration_portfolio = generate_portfolio(n=15_000, seed=42)
    engine = ActuarialEngine()
    engine.fit(calibration_portfolio)

    to_seed = generate_portfolio(n=n, seed=seed_value)
    rng = random.Random(seed_value)

    db = SessionLocal()
    n_policies = 0
    n_claims = 0
    try:
        for i, row in to_seed.reset_index(drop=True).iterrows():
            contract = {
                "age_conducteur": int(row["age_conducteur"]),
                "anciennete_permis": int(row["anciennete_permis"]),
                "usage": row["usage"],
                "zone": row["zone"],
                "puissance_cv": int(row["puissance_cv"]),
                "valeur_vehicule_fcfa": float(row["valeur_vehicule_fcfa"]),
                "garantie": row["garantie"],
                "nb_sinistres_anterieurs": int(row["nb_sinistres_anterieurs"]),
                "coefficient_bonus_malus": 1.0,
            }
            result = engine.price(contract)
            reg_check = check_minimum_tariff(COUNTRY, PRODUCT, result.prime_commerciale)

            birth_date = date(TODAY.year - int(row["age_conducteur"]), rng.randint(1, 12), rng.randint(1, 28))
            customer = crud.create_customer(
                db,
                {
                    "first_name": f"Client{i:05d}",
                    "last_name": "Démo",
                    "birth_date": birth_date,
                    "gender": row["sexe"],
                    "profession": "professionnel" if row["usage"] == "professionnel" else None,
                    "city": "Bangui" if row["zone"] == "bangui" else "Province",
                    "country": "CF",
                },
            )

            brand, model, vehicle_type = rng.choice(VEHICLES)
            vehicle = crud.create_vehicle(
                db,
                customer.id,
                {
                    "registration_number": f"RCA-{i:05d}",
                    "brand": brand,
                    "model": model,
                    "year": int(row["annee_vehicule"]),
                    "vehicle_type": vehicle_type,
                    "power": int(row["puissance_cv"]),
                    "market_value": float(row["valeur_vehicule_fcfa"]),
                    "usage": row["usage"],
                },
            )

            start_date = TODAY - timedelta(days=rng.randint(0, 700))
            end_date = start_date + timedelta(days=365)
            policy = crud.create_policy(
                db,
                customer.id,
                vehicle.id,
                {
                    "product": PRODUCT,
                    "start_date": start_date,
                    "end_date": end_date,
                    "coverage": row["garantie"],
                    "deductible": 0.0,
                    "premium": result.prime_commerciale,
                    "status": "active",
                },
            )

            crud.record_pricing_result(
                db,
                policy_id=policy.id,
                model_version=MODEL_VERSION,
                regulatory_version=reg_check.rule.regulatory_version if reg_check.rule else None,
                input_data=contract,
                frequency=result.frequence_estimee,
                severity=result.cout_moyen_estime,
                pure_premium=result.prime_pure,
                expenses=result.frais_gestion + result.marge_technique,
                margin=result.marge_technique,
                commercial_premium=result.prime_commerciale,
            )
            n_policies += 1

            nb_sinistres = int(row["nb_sinistres"])
            cout_moyen = float(row["cout_moyen_sinistre"]) if nb_sinistres > 0 else 0.0
            for _ in range(nb_sinistres):
                claim_date = start_date + timedelta(days=rng.randint(0, 364))
                crud.create_claim(
                    db,
                    {
                        "policy_id": policy.id,
                        "claim_date": claim_date,
                        "claim_type": rng.choice(CLAIM_TYPES),
                        "claim_amount": cout_moyen,
                        "paid_amount": cout_moyen,
                        "reserved_amount": 0.0,
                        "responsibility": 1.0,
                        "status": "closed",
                    },
                )
                n_claims += 1

        db.commit()
    finally:
        db.close()

    print(f"{n_policies} polices et {n_claims} sinistres insérés.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=500, help="Nombre de polices à générer")
    args = parser.parse_args()
    seed(args.n)
