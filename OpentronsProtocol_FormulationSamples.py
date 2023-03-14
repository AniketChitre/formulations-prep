#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipetting procedure to prepare shampoo formulations in 15g cosmetic jars.
Follow the `loc_dict` for placing the ingredients in the correct positions.

Start with the ingredient falcon tubes approx. 25 mL full and the water tubes filled till 35 mL.

Last Updated: 08.12.22

@author: Aniket Chitre
"""

# %% Section O: Preamble and install packages

# N.b. OT cannot install many packages, incl. those compiled in other languages - e.g., Numpy in C

import pandas as pd
import json
from opentrons import protocol_api

metadata = {
    'protocolName': 'Shampoo Formulations Preparation',
    'author': 'Aniket Chitre',
    'description': 'Opentrons protocol to prepare liquid formulations on a mass basis',
    'apiLevel': '2.11'  # https://docs.opentrons.com/v2/versioning.html
}

# %% Section 1: Define custom functions for handling viscous liquids & obtaining a reading from the mass balance


def run(protocol: protocol_api.ProtocolContext):
    # N.b. The entire protocol must be defined at this indented level within the run function.

    # `aspirate_viscous` and `dispense_viscous` modified from the OT documentation helper functions: https://opentrons-landing-img.s3.amazonaws.com/application+notes/Viscous+Liquids+App+Note.pdf

    def aspirate_viscous(pipette, volume, well, asp_height, asp_rate, asp_delay, drip_delay, asp_touch_tip, asp_with):
        """
        Custom function slows down the aspiration rate, adding a delay (to ensure complete aspiration), slows tip withdrawal and touches tip to remove any excess fluid

        input:
        pipette       = which pipette tips (e.g., p1000)
        volume        = aspiration volume/uL
        well          = position to aspirate from
        asp_height    = immersion depth for pipetting/mm
        asp_rate      = aspirate rate - times default flow_rate e.g., 0.5 is half the aspiration rate for water
        asp_delay     = aspiration delay/s
        drip_delay    = delay at the top of the tube before touch_tip to allow excess surfactant to drip off/s
        asp_touch_tip = number of touch_tips to remove XS liquid from the pipette tip after aspiration
        asp_with      = speed of pipette withdrawal/mm/s
        """

        pipette.move_to(well.top())  # move to top of labware at default protocol speed
        pipette.aspirate(volume, well.bottom(z=asp_height), rate=asp_rate)  # aspirate at a reduced flowrate from a set height measured from the bottom of the labware
        protocol.delay(asp_delay)  # add delay after aspiration for the liquid to aspirate completely
        pipette.move_to(well.top(z=-2), speed=asp_with)  # slowly move to top of labware
        protocol.delay(drip_delay)  # add delay once the tip has moved to the top of the labware for any excess fluid to drip off

        # Use touch_tip function to remove remaining exterior excess fluid
        if asp_touch_tip == 0:
            pass
        else:
            for i in range(asp_touch_tip):
                pipette.touch_tip(radius=0.98, v_offset=-3)  # radius = proportion of the target well's radius
                # v_offset default = 3 mm below top.

    def dispense_viscous(pipette, volume, disp_well, disp_rate, disp_delay, blowout_rate, blowout_cycles):
        """
        Custom function for a strategy to dispense viscous fluids - slower dispense, added delay, removing residual liquids with blowout

        input:
        pipette        = which pipette tips (e.g., p1000 - depends on labware definitions)
        volume         = dispense volume/uL
        disp_well      = position to dispense to
        disp_rate      = dispense rate - times default flow_rate.dispense (which is for e.g., 1000 uL/s for p1000 tip)
        disp_delay     = dispense delay/s
        blowout_rate   = blow out rate/uL/s
        blowout_cycles = number of rounds of blowout
        """

        pipette.dispense(volume, disp_well.top(z=-5), rate=disp_rate)  # dispense at a slower flowrate 5 mm below top of jar
        protocol.delay(disp_delay)  # allow the excess liquid in tip to settle towards tip orifice

        # Blowout
        def_pipette = pipette.flow_rate.blow_out  # save the default blow out rate as a variable
        pipette.flow_rate.blow_out = blowout_rate  # change the blow out rate to your custom definition
        for i in range(blowout_cycles):  # W.Y - needs multiple iterations for viscous fluids
            pipette.blow_out()  # perform blowout at the bottom of the labware at this slower rate
        pipette.flow_rate.blow_out = def_pipette  # set back to default blow out rate


    def move_viscous(pipette, source, destination, volume, asp_height, asp_rate, asp_delay, drip_delay, disp_rate, disp_delay, blowout_rate,
                     asp_touch_tip, asp_with, blowout_cycles):
        """
        Combining aspiration & dispensing and accounting for any iterations which will be required if the volume to be transferred is greater than the pipette's max volume.
        This is automatically implemented when calling the .transfer() method (volumes larger than the pipette's max volume will be divided into smaller transfers), but must be hard coded here.

        input:
        pipette      = which pipette tips (e.g., p1000)
        source       = source well
        destination  = destination well
        volume       = transfer volume/uL
        ...
        The remaining variables are defined the same way as in the above aspirate_viscous and dispense_viscous functions
        """

        if volume > pipette.max_volume:
            iterations = int(volume // pipette.max_volume) if volume % pipette.max_volume == 0 else int(volume // pipette.max_volume) + 1  # is the requested volume exactly divisible into the volume of the pipette; if not, roll the number to the next integer after floor division
            new_volume = round(volume / iterations, 2)

            for i in range(iterations):
                aspirate_viscous(pipette, new_volume, source, asp_height, asp_rate, asp_delay, drip_delay, asp_touch_tip, asp_with)
                dispense_viscous(pipette, new_volume, destination, disp_rate, disp_delay, blowout_rate, blowout_cycles)

        else:
            aspirate_viscous(pipette, volume, source, asp_height, asp_rate, asp_delay, drip_delay, asp_touch_tip, asp_with)
            dispense_viscous(pipette, volume, destination, disp_rate, disp_delay, blowout_rate, blowout_cycles)

    # %% Section 2: Define labware

    # json files defining the custom labware are directly coded here, so they do not need to be separately uploaded to the laptop controlling the OT-2
    # json files created from the Opentrons Custom Labware Creator (online web app): https://labware.opentrons.com/create/

    AMDM_12_50ml_falcon_tube_DEF_JSON = """{
        "ordering":[["A1","B1","C1"],["A2","B2","C2"],["A3","B3","C3"],["A4","B4","C4"]],
        "brand":{"brand":"AMDM","brandId":["AMDM"]},
        "metadata":{"displayName":"AMDM 12 50ml falcon tube","displayCategory":"reservoir","displayVolumeUnits":"µL","tags":[]},
        "dimensions":{"xDimension":127.76,"yDimension":85.47,"zDimension":119.36},
        "wells":{"A1":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":21,"y":70.97,"z":5.4},"B1":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":21,"y":43.61,"z":5.4},"C1":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":21,"y":15.25,"z":5.4},"A2":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":48.6,"y":70.97,"z":5.4},"B2":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":48.6,"y":43.61,"z":5.4},"C2":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":48.6,"y":15.25,"z":5.4},"A3":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":77.2,"y":70.97,"z":5.4},"B3":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":77.2,"y":43.61,"z":5.4},"C3":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":77.2,"y":15.25,"z":5.4},"A4":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":105.8,"y":70.97,"z":5.4},"B4":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":105.8,"y":43.61,"z":5.4},"C4":{"depth":116,"totalLiquidVolume":50000,"shape":"circular","diameter":27.44,"x":105.8,"y":15.25,"z":5.4}},
        "groups":[{"metadata":{"wellBottomShape":"v"},"wells":["A1","B1","C1","A2","B2","C2","A3","B3","C3","A4","B4","C4"]}],
        "parameters":{"format":"irregular",
        "quirks":[],
        "isTiprack":false,
        "isMagneticModuleCompatible":false,
        "loadName":"amdm_12_50ml_falcon_tube"},
        "namespace":"custom_beta",
        "version":1,
        "schemaVersion":2,
        "cornerOffsetFromSlot":{"x":0,"y":0,"z":0}}"""

    COSMETIC_JARS_RAISED_BALANCE = """{
    "ordering": [["A1","B1"],["A2","B2"],["A3","B3"]],
    "brand": {"brand": "AMDM","brandId": []},"metadata": {"displayName": "AMDM Cosmetic Jar Holder Over Balance",
    "displayCategory": "tubeRack","displayVolumeUnits": "µL","tags": []},
    "dimensions": {"xDimension": 127.71,"yDimension": 85.43,"zDimension": 50},
    "wells": {"A1": {"depth": 23,"totalLiquidVolume": 15000,"shape": "circular","diameter": 33.2,"x": 20.8,"y": 64.63,"z": 27},"B1": {"depth": 23,"totalLiquidVolume": 15000,"shape": "circular","diameter": 33.2,"x": 20.8,"y": 21.23,"z": 27},
    "A2": {"depth": 23,"totalLiquidVolume": 15000,"shape": "circular","diameter": 33.2,"x": 64.2,"y": 64.63,"z": 27},"B2": {"depth": 23,"totalLiquidVolume": 15000,"shape": "circular","diameter": 33.2,"x": 64.2,"y": 21.23,"z": 27},
    "A3": {"depth": 23,"totalLiquidVolume": 15000,"shape": "circular","diameter": 33.2,"x": 107.6,"y": 64.63,"z": 27},"B3": {"depth": 23,"totalLiquidVolume": 15000,"shape": "circular","diameter": 33.2,"x": 107.6,"y": 21.23,"z": 27}},
    "groups": [{"brand": {"brand": "AMDM","brandId": []},"metadata": {"wellBottomShape": "flat","displayCategory": "tubeRack"},"wells": ["A1","B1","A2","B2","A3","B3"]}],
    "parameters": {"format": "irregular","quirks": [],"isTiprack": false,"isMagneticModuleCompatible": false,"loadName": "15g_cosmetic_jars_balance"},"namespace": "custom_beta","version": 1,"schemaVersion": 2,"cornerOffsetFromSlot": {"x": 0,"y": 0,"z": 0}}"""

    AMDM_12_50ml_falcon_tube = json.loads(AMDM_12_50ml_falcon_tube_DEF_JSON)
    Cosmetic_Jars_Raised_Balance = json.loads(COSMETIC_JARS_RAISED_BALANCE)

    # 2nd argument (#) corresponds to OT-2 slot position
    ingredients_1 = protocol.load_labware_from_definition(AMDM_12_50ml_falcon_tube, 5)  # anionic + non-ionic surfactants
    ingredients_2 = protocol.load_labware_from_definition(AMDM_12_50ml_falcon_tube, 9)  # amphoteric surfactants + water
    ingredients_3 = protocol.load_labware_from_definition(AMDM_12_50ml_falcon_tube, 8)  # amino-acid based + cationic surfactant + thickeners
    ingredients_4 = protocol.load_labware_from_definition(AMDM_12_50ml_falcon_tube, 6)  # conditioning polymers + water

    formulations = protocol.load_labware_from_definition(Cosmetic_Jars_Raised_Balance, 2)  # samples 1-6

    tiprack_1 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', 3)  # using wide-bore pipette tips
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=[tiprack_1])

    dest_list = formulations.wells()
                       
    ingredient_list = ['Texapon SB 3 KC', 'Plantapon ACG 50', 'Plantapon LC 7',
                   'Plantacare 818', 'Plantacare 2000',
                   'Dehyton MC', 'Dehyton PK 45', 'Dehyton ML', 'Dehyton AB 30',
                   'Plantapon Amino SCG-L', 'Plantapon Amino KG-L','Dehyquart A-CA',
                   'Luviquat Excellence', 'Dehyquart CC6',
                   'Dehyquart CC7 Benz', 'Salcare Super 7', 'Arlypon F', 'Arlypon TT', 'Water']

    loc_dict = {'Texapon SB 3 KC': ingredients_1['A1'], 'Plantapon ACG 50': ingredients_1['C1'], 'Plantapon LC 7': ingredients_1['B2'],
                'Plantacare 818': ingredients_1['A3'],'Plantacare 2000': ingredients_1['B4'],
                'Dehyton MC': ingredients_2['A1'], 'Dehyton PK 45': ingredients_2['C1'],'Dehyton ML': ingredients_2['A3'],
                'Dehyton AB 30': ingredients_2['C3'],'Plantapon Amino SCG-L': ingredients_3['A1'], 'Plantapon Amino KG-L': ingredients_3['C1'],
                'Dehyquart A-CA': ingredients_3['A3'],'Luviquat Excellence': ingredients_4['A1'],
                'Dehyquart CC6': ingredients_4['A3'], 'Dehyquart CC7 Benz': ingredients_4['C3'],'Salcare Super 7': ingredients_4['C1'],
                'Arlypon F': ingredients_3['C3'], 'Arlypon TT': ingredients_3['B4']}

    density_dict = {'Texapon SB 3 KC': 1.128, 'Plantapon ACG 50': 1.147, 'Plantapon LC 7': 1.070,
                    'Plantacare 818': 1.104, 'Plantacare 2000': 1.103,
                    'Dehyton MC': 1.097, 'Dehyton PK 45': 1.062, 'Dehyton ML': 1.084, 'Dehyton AB 30': 1.031,
                    'Plantapon Amino SCG-L': 1.051, 'Plantapon Amino KG-L': 1.028,'Dehyquart A-CA': 0.955,
                    'Luviquat Excellence': 1.118, 'Dehyquart CC6': 1.067,
                    'Dehyquart CC7 Benz': 1.024, 'Salcare Super 7': 1.121, 'Arlypon F': 0.887, 'Arlypon TT': 0.970, 'Water': 0.998}

    # %% Section 3: DoE and formulation ingredients liquid handling parameters

    DoE = pd.read_csv(r'/var/lib/jupyter/notebooks/SuggestedExperiments/MasterDataset_OT_DoE_10-14-03-23.csv', index_col=0)
    DoE = DoE.loc[:, ~DoE.columns.str.contains('^Unnamed')]  # drop any unnamed columns resulting from formatting issues when saving .xlsx to .csv

    # Excel workbook contains mass_fraction, but need to convert this to a volume for the Opentrons to dispense
    V_tot = 10000  # ~ require approx. 8-10 mL to submerge the pH probe sufficiently in the pH adjustment step

    # Edit these each run :)
    start_sample_idx = 175
    end_sample_idx = 180

    vol_dict = {i: list(round(V_tot*((DoE[i].iloc[start_sample_idx-1:end_sample_idx]*DoE['Sample Density'].iloc[start_sample_idx-1:end_sample_idx])/(100*density_dict[i])))) for i in ingredient_list}

    vol_df = pd.DataFrame.from_dict(vol_dict)
    #vol_df.index = np.arange(1, len(vol_df) + 1)

    water_vol = vol_df['Water'].tolist()

    # Liquid handling parameters by class of ingredient (S/P/T) - only loosely optimised.

    # Surfactants - initial results suggest could be further optimised
    S = {
        'asp_rate': 0.10,
        'asp_delay': 4,
        'drip_delay': 6,
        'disp_rate': 0.2,
        'disp_delay': 3,
        'blowout_rate': 5,
        'asp_with': 10,
        'asp_touch_tip': 2,
        'blowout_cycles': 3
    }

    # Polyelectrolytes - initial results suggest fairly well optimised
    P = {
        'asp_rate': 0.05,
        'asp_delay': 4,
        'drip_delay': 6,
        'disp_rate': 0.05,
        'disp_delay': 5,
        'blowout_rate': 5,
        'asp_with': 2,
        'asp_touch_tip': 3,
        'blowout_cycles': 5
    }

    # Thickeners - contrary to their name, they are easy to pipette
    T = {
        'asp_rate': 0.75,
        'asp_delay': 0.5,
        'drip_delay': 0.5,
        'disp_rate': 0.75,
        'disp_delay': 2,
        'blowout_rate': 75,
        'asp_with': 20,
        'asp_touch_tip': 0,
        'blowout_cycles': 2
    }

    # %% Section 4: Prepare formulations

    # slow down movement to prevent shaking
    p1000.default_speed = 200  # mm/s

    p1000.well_bottom_clearance.aspirate = 15  # 15 mm clearance
    p1000.well_bottom_clearance.dispense = 20  # 20 mm clearance - depth of cosmetic jar = 25 mm - 20, therefore water dispensed from 5 mm from top

    asp_h = 35  # 35 mm from the bottom corresponds to 15 mL mark on the falcon tube --> chosen as an inch below ~ 20-25 mL

    # =================================================================================
    # Transfer of water - formulation's base
    # =================================================================================

    #Place 2 tubes of water in positions ingredients_2['B4'] (slot #1) and ingredients_4['B4'] (slot #6)

    p1000.pick_up_tip() 
    for i in range(6):
        if i < 3:
            p1000.transfer(water_vol[i], ingredients_2['B4'], dest_list[i], new_tip='never')
        elif i < 6:
           p1000.transfer(water_vol[i], ingredients_4['B4'], dest_list[i], new_tip='never')
    p1000.drop_tip()

    # =================================================================================
    # Transfer surfactants
    # =================================================================================

    surfactants = ingredient_list[0:12]

    # iterating through the chemicals and accessing the required volumes and location through dictionary definitions

    for x in surfactants:
        if sum(vol_dict[x]) != 0:
            p1000.pick_up_tip()
            for i in range(6):
                if vol_dict[x][i] != 0:
                    move_viscous(p1000, loc_dict[x], dest_list[i], vol_dict[x][i], asp_h,
                                 S['asp_rate'], S['asp_delay'], S['drip_delay'],
                                 S['disp_rate'], S['disp_delay'], S['blowout_rate'],
                                 S['asp_touch_tip'], S['asp_with'], S['blowout_cycles'])
            p1000.drop_tip()


    # =================================================================================
    # Transfer polyelectrolyte
    # =================================================================================

    polyelectrolytes = ingredient_list[12:16]

    for y in polyelectrolytes:
        if sum(vol_dict[y]) != 0:
            p1000.pick_up_tip()
            for i in range(6):
                if vol_dict[y][i] != 0:
                    move_viscous(p1000, loc_dict[y], dest_list[i], vol_dict[y][i], asp_h,
                                 P['asp_rate'], P['asp_delay'], P['drip_delay'],
                                 P['disp_rate'], P['disp_delay'], P['blowout_rate'],
                                 P['asp_touch_tip'], P['asp_with'], P['blowout_cycles'])
            p1000.drop_tip()


    # =================================================================================
    # Transfer thickener
    # =================================================================================

    thickeners = ingredient_list[16:18]

    for z in thickeners:
        if sum(vol_dict[z]) != 0:
            p1000.pick_up_tip()
            for i in range(6):
                if vol_dict[z][i] != 0:
                    move_viscous(p1000, loc_dict[z], dest_list[i], vol_dict[z][i], asp_h,
                                 T['asp_rate'], T['asp_delay'], T['drip_delay'],
                                 T['disp_rate'], T['disp_delay'], T['blowout_rate'],
                                 T['asp_touch_tip'], T['asp_with'], T['blowout_cycles'])
                    protocol.delay(4) # 4 seconds delay between each thickener step
            p1000.drop_tip()