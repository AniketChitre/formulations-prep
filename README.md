# Liquid Formulations Prepartion
Protocols and codes to prepare and analyse the composition of the formulations. 

The Opentrons OT-2, automated pipetting robot, is used to prepare the liquid formulations from a set of selected (viscous) industrial ingredients. The `OpentronsProtocol_FormulationSamples.py` is uploaded to the OT-2 to run the designed protocol for automated viscous liquids handling. The file needs to be edited to select which formulations to prepare.

As discussed in our [Opentrons application note](https://insights.opentrons.com/hubfs/20230823%20Mass%20Balance%20Integration%20App%20Note%20Final.pdf), a mass balance is run concurrently to log data during the Opentrons run with the `OT-2_BalanceAutomation.ipynb` Jupyter Notebook and the resulting data can be deconvoluted into the formulation compositions with `balance_analysis.ipynb`.
