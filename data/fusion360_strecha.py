"""Fusion 360 skript - parametricky zaklad strechy Vsenory, Vaclava Krena 140.

JAK SPUSTIT:
  1. Ve Fusion 360: Utilities -> ADD-INS -> Scripts and Add-Ins (zkratka Shift+S)
  2. Zalozka Scripts -> zelene "+" -> vybrat slozku s timto souborem
  3. Oznacit "StrechaVsenory" -> Run

CO TO POSTAVI:
  - Tri stresni plochy (Jih / Zapad / Vychod) jako lichobezniky ve spravnem
    sklonu 38,9 st. a spravnych azimutech, slozene do jednoho telesa strechy
  - Komin jako kvadr s ODHADNUTYMI rozmery - ten dokresli/uprav rucne
  - Vsechny rozmery jsou POJMENOVANE PARAMETRY (Modify -> Change Parameters),
    takze zmenou jednoho cisla se prepocita cely model

SOURADNY SYSTEM:
  X = vychod, Y = sever, Z = vzhuru. Pocatek = stred okapu jizni plochy.
  Azimut se meri od severu po smeru hodinovych rucicek (jih = 180 st.).

POZOR: rozmery ploch jsou zamerene POUZE PO PATU KOMINU. Komin sam zameren
neni - jeho rozmery v tomto skriptu jsou odhad, ktery je potreba nahradit
skutecnymi hodnotami (viz JAK_MERIT.md).
"""
import math

import adsk.core
import adsk.fusion
import traceback

# ---------------------------------------------------------------------------
# ZAMERENE HODNOTY (2026_Strecha/po_premereni/poptana_varianta/README.md)
# ---------------------------------------------------------------------------
SKLON_DEG = 38.9

PLOCHY = [
    # nazev,    azimut, okap [m], spadnice [m], horni hrana [m], panelu
    ("Jih",     158.0,  12.69,    4.62,         5.49,            9),
    ("Zapad",   248.0,  10.81,    4.60,         3.64,            10),
    ("Vychod",   68.0,  10.81,    3.85,         4.81,            9),
]

# ---------------------------------------------------------------------------
# ODHAD - NUTNO NAHRADIT SKUTECNYMI ROZMERY PO ZAMERENI
# ---------------------------------------------------------------------------
KOMIN_SIRKA = 0.60      # rozmer v ose vychod-zapad [m]
KOMIN_HLOUBKA = 0.45    # rozmer v ose sever-jih [m]
KOMIN_VYSKA = 1.20      # vyska nad bodem vystupu ze strechy [m]
KOMIN_POSUN_U = 0.0     # posun podel horni hrany Vychodu od stredu [m]

M = 100.0               # Fusion pracuje v cm


def run(context):
    """Vstupni bod skriptu Fusion 360.

    :param context: kontext predany Fusionem
    """
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent

        _vytvor_parametry(design)

        for nazev, azimut, okap, spadnice, horni, panelu in PLOCHY:
            _plocha(root, nazev, azimut, okap, spadnice, horni)

        _komin(root)

        app.activeViewport.fit()
        ui.messageBox(
            "Strecha Vsenory postavena.\n\n"
            "Tri plochy ve sklonu 38,9 st. + komin (ODHAD rozmeru).\n\n"
            "Rozmery zmenis v Modify -> Change Parameters:\n"
            "  komin_vyska, komin_sirka, komin_hloubka, komin_posun\n\n"
            "Rozmery kominu jsou zatim ODHAD - nahrad je skutecnymi\n"
            "po zamereni (viz JAK_MERIT.md).")

    except:  # noqa: E722 - Fusion vyzaduje holy except pro zobrazeni chyby
        if ui:
            ui.messageBox("Skript selhal:\n{}".format(traceback.format_exc()))


def _vytvor_parametry(design):
    """Zalozi pojmenovane uzivatelske parametry.

    :param design: aktivni navrh Fusionu
    """
    p = design.userParameters
    units = design.unitsManager

    def add(name, value_cm, comment):
        if p.itemByName(name):
            return
        p.add(name, adsk.core.ValueInput.createByReal(value_cm),
              units.defaultLengthUnits, comment)

    add("sklon_strechy", SKLON_DEG, "Sklon vsech ploch [deg] - zamereno")
    add("komin_vyska", KOMIN_VYSKA * M, "ODHAD - vyska kominu nad strechou")
    add("komin_sirka", KOMIN_SIRKA * M, "ODHAD - sirka kominu (vychod-zapad)")
    add("komin_hloubka", KOMIN_HLOUBKA * M, "ODHAD - hloubka kominu (sever-jih)")
    add("komin_posun", KOMIN_POSUN_U * M, "ODHAD - posun podel horni hrany")


def _baze(azimut_deg):
    """Bazove vektory stresni plochy v ENU.

    :param azimut_deg: azimut plochy od severu po smeru hod. rucicek
    :returns: (e_u podel okapu, e_v po spadnici, normala)
    """
    a = math.radians(azimut_deg)
    t = math.radians(SKLON_DEG)
    e_u = adsk.core.Vector3D.create(math.cos(a), -math.sin(a), 0.0)
    e_v = adsk.core.Vector3D.create(-math.sin(a) * math.cos(t),
                                    -math.cos(a) * math.cos(t),
                                    math.sin(t))
    n = adsk.core.Vector3D.create(math.sin(t) * math.sin(a),
                                  math.sin(t) * math.cos(a),
                                  math.cos(t))
    return e_u, e_v, n


def _bod(origin, e_u, e_v, u, v):
    """Prevede 2D souradnice plochy na 3D bod ve Fusionu (v cm).

    :param origin: pocatek plochy (Point3D, cm)
    :param e_u: jednotkovy vektor podel okapu
    :param e_v: jednotkovy vektor po spadnici
    :param u: souradnice podel okapu [m]
    :param v: souradnice po spadnici [m]
    :returns: Point3D v cm
    """
    return adsk.core.Point3D.create(
        origin.x + (u * e_u.x + v * e_v.x) * M,
        origin.y + (u * e_u.y + v * e_v.y) * M,
        origin.z + (u * e_u.z + v * e_v.z) * M)


def _plocha(root, nazev, azimut, okap, spadnice, horni):
    """Vytvori jednu stresni plochu jako lichobeznikovou desku.

    :param root: korenova komponenta
    :param nazev: nazev plochy
    :param azimut: azimut plochy [deg]
    :param okap: sirka u okapu [m]
    :param spadnice: delka spadnice [m]
    :param horni: sirka u horni hrany (pata kominu) [m]
    """
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = nazev

    e_u, e_v, n = _baze(azimut)
    origin = adsk.core.Point3D.create(0, 0, 0)

    # Rovina plochy: prochazi okapem, natocena podle azimutu a sklonu
    sk = comp.constructionPlanes.createInput()
    sk.setByPlaneAndOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(0))
    sketch = comp.sketches.add(root.xYConstructionPlane)

    he, ht = okap / 2.0, horni / 2.0
    body = [_bod(origin, e_u, e_v, -he, 0.0),
            _bod(origin, e_u, e_v, he, 0.0),
            _bod(origin, e_u, e_v, ht, spadnice),
            _bod(origin, e_u, e_v, -ht, spadnice)]

    lines = sketch.sketchCurves.sketchLines
    for i in range(4):
        lines.addByTwoPoints(body[i], body[(i + 1) % 4])

    prof = sketch.profiles.item(0)
    ext = comp.features.extrudeFeatures.createInput(
        prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext.setDistanceExtent(False, adsk.core.ValueInput.createByReal(5.0))  # 5 cm tl.
    comp.features.extrudeFeatures.add(ext)


def _komin(root):
    """Vytvori komin jako kvadr na horni hrane vychodni plochy.

    Poloha je ODHAD - komin stoji na horni hrane Vychodu (pata kominu),
    tedy tam, kde konci zamerena plocha.

    :param root: korenova komponenta
    """
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = "Komin_ODHAD"

    _, _, _ = _baze(68.0)
    e_u, e_v, _ = _baze(68.0)
    origin = adsk.core.Point3D.create(0, 0, 0)

    # Pata kominu = horni hrana vychodni plochy (v = spadnice)
    pata = _bod(origin, e_u, e_v, KOMIN_POSUN_U, 3.85)

    sketch = comp.sketches.add(root.xYConstructionPlane)
    hw, hd = KOMIN_SIRKA / 2.0 * M, KOMIN_HLOUBKA / 2.0 * M
    rohy = [adsk.core.Point3D.create(pata.x - hw, pata.y - hd, pata.z),
            adsk.core.Point3D.create(pata.x + hw, pata.y - hd, pata.z),
            adsk.core.Point3D.create(pata.x + hw, pata.y + hd, pata.z),
            adsk.core.Point3D.create(pata.x - hw, pata.y + hd, pata.z)]
    lines = sketch.sketchCurves.sketchLines
    for i in range(4):
        lines.addByTwoPoints(rohy[i], rohy[(i + 1) % 4])

    prof = sketch.profiles.item(0)
    ext = comp.features.extrudeFeatures.createInput(
        prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext.setDistanceExtent(False, adsk.core.ValueInput.createByReal(KOMIN_VYSKA * M))
    comp.features.extrudeFeatures.add(ext)
