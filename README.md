# Prepare Liquid Formulations
Protocols and codes to prepare and analyse the composition of the formulations

The Opentrons-2, automated pipetting robot, is being used to prepare the liquid formulations from the set of selected (viscous) industrial ingredients. 

The `OpentronsProtocol` is the main file which needs to be uploaded to the Opentrons robot, which will read in the instructions of which formulations to make from the specified csv file stored in the `DoE_csv` directory. The design of experiments are selected through the code in the `DoE_Generator` jupyter notebook. 

During a run the lab laptop needs to be connected to the mass balance integrated under the OT-2 in our lab and the `OT-2_BalanceAutomation` file needs to be run, which will record the mass data from the balance. This outputs a csv to the `mass_data` directory, which will then be read in, along with the instructions and `SpeciesDictionary` to `balance_analysis` code. This runs a set of actions defined in `PipettingMassBalance` to deconvolute the mass vs. time profile into the mass of each ingredient added into each sample, ultimately, presenting the formulaton as it actual composition in mass %. 
