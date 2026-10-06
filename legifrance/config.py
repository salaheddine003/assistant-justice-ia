# ── Credentials Legifrance API (PISTE) ───────────────────────────────────────
# Never commit credentials. Configure these values in .env or in the process
# environment. Previously committed credentials must be revoked in PISTE.
import os as _os

CLIENT_ID     = _os.getenv("PISTE_CLIENT_ID", "")
CLIENT_SECRET = _os.getenv("PISTE_CLIENT_SECRET", "")
API_KEY       = _os.getenv("PISTE_API_KEY", "")

OAUTH_URL  = "https://oauth.piste.gouv.fr/api/oauth/token"
API_BASE   = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
LEGIFRANCE = "https://www.legifrance.gouv.fr"

from datetime import date as _date

PDF_FOLDER  = "pdfs"
PDF_FOLDER2 = "pdfs2"
WORKERS     = 10
DATE_REF    = _date.today().isoformat()  # toujours la date du jour

# ── Les 20 principaux codes français (dossier pdfs/) ─────────────────────────
CODES = {
    "Code civil":                          "LEGITEXT000006070721",
    "Code penal":                          "LEGITEXT000006070719",
    "Code de procedure penale":            "LEGITEXT000006071154",
    "Code du travail":                     "LEGITEXT000006072050",
    "Code de commerce":                    "LEGITEXT000005634379",
    "Code general des impots":             "LEGITEXT000006069577",
    "Code de la sante publique":           "LEGITEXT000006072665",
    "Code de la securite sociale":         "LEGITEXT000006073189",
    "Code de l environnement":             "LEGITEXT000006074220",
    "Code de l urbanisme":                 "LEGITEXT000006074075",
    "Code de l education":                 "LEGITEXT000006071191",
    "Code de la consommation":             "LEGITEXT000006069565",
    "Code des transports":                 "LEGITEXT000023086525",
    "Code de la defense":                  "LEGITEXT000006071307",
    "Code rural":                          "LEGITEXT000006071367",
    "Code monetaire et financier":         "LEGITEXT000006072026",
    "Code de la construction":             "LEGITEXT000006074096",
    "Code des assurances":                 "LEGITEXT000006073984",
    "Code de la propriete intellectuelle": "LEGITEXT000006069414",
    "Code des douanes":                    "LEGITEXT000006071570",
}

# ── Codes supplémentaires (dossier pdfs2/) ────────────────────────────────────
CODES2 = {
    # ── Codes administratifs ─────────────────────────────────────────────────
    "Code de justice administrative":              "LEGITEXT000006070933",
    "Code des juridictions financieres":           "LEGITEXT000006070249",
    "Code general des collectivites territoriales": "LEGITEXT000006070633",
    "Code des relations entre le public et l administration": "LEGITEXT000031366350",
    "Code de l organisation judiciaire":           "LEGITEXT000006071164",
    "Code general de la propriete des personnes publiques": "LEGITEXT000006070299",
    "Code de l expropriation":                     "LEGITEXT000027248910",
    # ── Procédures ───────────────────────────────────────────────────────────
    "Code de procedure civile":                    "LEGITEXT000006070716",
    "Code des procedures civiles d execution":     "LEGITEXT000025024948",
    # ── Codes spécialisés ────────────────────────────────────────────────────
    "Code de la route":                            "LEGITEXT000006074228",
    "Code de l action sociale et des familles":    "LEGITEXT000006074069",
    "Code de la securite interieure":              "LEGITEXT000025503132",
    "Code du sport":                               "LEGITEXT000006071318",
    "Code electoral":                              "LEGITEXT000006070239",
    "Code forestier":                              "LEGITEXT000025244092",
    "Code de la commande publique":                "LEGITEXT000037701019",
    "Code de la fonction publique":                "LEGITEXT000044416551",
    "Code de l entree et du sejour des etrangers": "LEGITEXT000006070158",
    "Code du tourisme":                            "LEGITEXT000006074073",
    "Code de l energie":                           "LEGITEXT000023983208",
    "Code minier":                                 "LEGITEXT000023504962",
    "Code de la recherche":                        "LEGITEXT000006071190",
    "Code du cinema et de l image animee":         "LEGITEXT000020908868",
    "Code des pensions civiles et militaires":     "LEGITEXT000006070712",
    "Code des postes et des communications electroniques": "LEGITEXT000006070987",
    "Livre des procedures fiscales":               "LEGITEXT000006069583",
    # ── Codes API parfois indisponibles (tentative) ───────────────────────────
    "Code du patrimoine":                          "LEGITEXT000006074038",
    "Code penitentiaire":                          "LEGITEXT000043982732",
    "Code de la mutualite":                        "LEGITEXT000006074086",
    "Code de la voirie routiere":                  "LEGITEXT000006074746",
}
