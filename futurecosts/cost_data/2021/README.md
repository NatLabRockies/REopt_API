## PV Costs from NLR Annual Technology Baseline
Steps to create future costs for solar PV systems from the 2020 ATB Data Excel spreadsheet:
1. Go to the `Solar - PV Dist. Comm` tab
2. Select `CustomCRP` in the `Choose a Capital Recovery Period (CRP)` box and enter `25` years.
3. Click `Apply CRP to all Technologies`
4. Select `Market Factor Financials` in the `Financial Assumption` box
5. Click `Apply Finances to all Technologies`
6. Take `CAPEX` and `Fixed Operations and Maintenance Expenses` from the `Moderate` rows in `Future Projections` tables (any region since all regions show the same price)
The values from this process are saved in ATB_2021_PV_costs.csv.

## Wind Costs from "Assessing the Future of Distributed Wind: Opportunities for Behind-the-Meter Projects"
- Authors: Eric Lantz, Benjamin Sigrin, Michael Gleason, Robert Preus, and Ian Baring-Gould
- Institution: National Renewable Energy Laboratory
- Year: 2016
- URL: https://docs.nlr.gov/docs/fy17osti/67337.pdf

## Battery Costs

There is significant uncertainty surrounding battery cost estimates. The calculated replacement cost estimate used for a default value is N years of 5.5% per year cost declines from the default costs. This is a conservative estimate from the references below.

- U.S. Energy Storage Monitor: 2020 Year in Review Full Report. Wood Mackenzie Power & Renewables and the Energy Storage Association, March 2021.
- Woods Mackenzie predicts a decline in price of 15% in the next 2 years for front-of-the meter storage, but note a 5% decline in the past year for behind-the-meter non-residential. Pandemic has impacted demand and prices may see impact.
- BloombergNEF: Long-term Energy Storage Outlook 2020 Data Viewer, December 2020.
- Bloomberg NEF capital cost predictions show a decline between 2021 and 2030 which averaged 5.3% (3.1%-7.3%) for a residential system and 5.6% (3.9%-8.2%) for a utility scale system.
- [Energy Storage Technology and Cost Characterization Report.  Pacific Northwest National Laboratory. July 2019.](https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-28866.pdf)
    - A cost drop of 5% per year was assumed to be a conservative estimate for batteries on the lower end of the cost range. This is in light of significant cost drops seen in the past 10 years.