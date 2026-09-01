"""Génération d'un portefeuille habitation (multirisque habitation / MRH)
synthétique — même esprit que `data_simulation.py` (auto) : hypothèses de
démonstration documentées ci-dessous, pas des statistiques de marché
réelles, partagées par tous les pays CIMA en l'absence de données par pays
(voir `app/regulatory/cima_countries.py`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Hypothèses de sinistralité (log-fréquence de base et effets multiplicatifs)
BASE_LOG_FREQUENCY = -2.5
EFFECT_MATERIAUX_PRECAIRE = 0.90  # construction précaire : risque incendie/effondrement élevé
EFFECT_MATERIAUX_SEMI_DUR = 0.35
EFFECT_ZONE_URBAINE = 0.30  # risque de vol plus élevé en zone urbaine
EFFECT_SANS_SECURITE = 0.25  # absence de gardiennage/alarme
EFFECT_ANCIENNETE_BATIMENT = 0.012  # par année (plafonnée) : électricité/plomberie vieillissantes
EFFECT_SINISTRE_ANTERIEUR = 0.20  # par sinistre antérieur

# Hypothèses de coût moyen par sinistre (devise du contrat)
BASE_SEVERITY = 200_000.0
EFFECT_VALEUR_BATIMENT = 0.03  # part de la valeur du bâtiment assurée
EFFECT_VALEUR_CONTENU = 0.05  # part de la valeur du contenu assuré
EFFECT_MATERIAUX_PRECAIRE_SEVERITY = -30_000.0  # matériaux moins coûteux à reconstruire


def generate_habitation_portfolio(n: int = 15_000, seed: int = 42) -> pd.DataFrame:
    """Génère un portefeuille de contrats habitation avec sinistralité simulée."""
    rng = np.random.default_rng(seed)

    type_logement = rng.choice(["maison", "appartement"], size=n, p=[0.6, 0.4])
    zone = rng.choice(["urbain", "rural"], size=n, p=[0.65, 0.35])
    surface_m2 = rng.integers(25, 300, size=n)
    materiaux_construction = rng.choice(
        ["dur", "semi_dur", "precaire"], size=n, p=[0.55, 0.30, 0.15]
    )
    valeur_batiment = rng.lognormal(mean=16.0, sigma=0.6, size=n).round(-3)
    valeur_contenu = rng.lognormal(mean=14.5, sigma=0.6, size=n).round(-3)
    anciennete_batiment = rng.integers(0, 50, size=n)
    securite = rng.choice([True, False], size=n, p=[0.35, 0.65])
    nb_sinistres_anterieurs = rng.poisson(0.15, size=n)
    garantie = rng.choice(["incendie_simple", "multirisque"], size=n, p=[0.55, 0.45])
    exposition = np.ones(n)

    materiaux_precaire = (materiaux_construction == "precaire").astype(float)
    materiaux_semi_dur = (materiaux_construction == "semi_dur").astype(float)
    zone_urbain = (zone == "urbain").astype(float)
    sans_securite = (~securite).astype(float)
    anciennete_plafonnee = np.minimum(anciennete_batiment, 40)

    log_lambda = (
        BASE_LOG_FREQUENCY
        + EFFECT_MATERIAUX_PRECAIRE * materiaux_precaire
        + EFFECT_MATERIAUX_SEMI_DUR * materiaux_semi_dur
        + EFFECT_ZONE_URBAINE * zone_urbain
        + EFFECT_SANS_SECURITE * sans_securite
        + EFFECT_ANCIENNETE_BATIMENT * anciennete_plafonnee
        + EFFECT_SINISTRE_ANTERIEUR * nb_sinistres_anterieurs
    )
    lam = np.exp(log_lambda) * exposition
    nb_sinistres = rng.poisson(lam)

    mean_cost = (
        BASE_SEVERITY
        + EFFECT_VALEUR_BATIMENT * valeur_batiment
        + EFFECT_VALEUR_CONTENU * valeur_contenu
        + EFFECT_MATERIAUX_PRECAIRE_SEVERITY * materiaux_precaire
    )
    mean_cost = np.maximum(mean_cost, 20_000.0)
    shape = 2.0
    cost_draws = rng.gamma(shape=shape, scale=mean_cost / shape, size=n)
    cout_moyen_sinistre = np.where(nb_sinistres > 0, cost_draws, np.nan)

    return pd.DataFrame(
        {
            "type_logement": type_logement,
            "zone": zone,
            "surface_m2": surface_m2,
            "materiaux_construction": materiaux_construction,
            "valeur_batiment": valeur_batiment,
            "valeur_contenu": valeur_contenu,
            "anciennete_batiment": anciennete_batiment,
            "securite": securite,
            "nb_sinistres_anterieurs": nb_sinistres_anterieurs,
            "garantie": garantie,
            "exposition": exposition,
            "nb_sinistres": nb_sinistres,
            "cout_moyen_sinistre": cout_moyen_sinistre,
        }
    )
