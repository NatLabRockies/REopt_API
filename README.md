REopt® API
=========
The REopt® model in this repository is a free, open-source, development version of the [REopt API](https://developer.nlr.gov/docs/energy-optimization/reopt/). A production version of the REopt API lies behind the [REopt Web Tool](https://reopt.nlr.gov/tool).

The REopt API provides concurrent, multiple technology integration and optimization capabilities to help organizations meet their cost savings, energy performance, resilience, and emissions reduction goals. Formulated as a mixed integer linear program, the REopt model recommends an optimally sized mix of renewable energy, conventional generation, and energy storage technologies; estimates the net present value of implementing those technologies; and provides a dispatch strategy for operating the technology mix at maximum economic efficiency. A list of the REopt model capabilities is provided [here](https://reopt.nlr.gov/about/capabilities.html). Example projects using REopt can be viewed [here](https://reopt.nlr.gov/projects/).

## Should I be using or modifying the REopt API or the REopt Julia Package? 

The REopt Julia package is the backend of the REopt API. That means that the optimization model is contained in [REopt.jl](https://github.com/NatLabRockies/REopt.jl), and that a user could supply the same inputs to the API and Julia package and get the same results. So which should you use? 

**1. When and how to _use_ the REopt Julia package:**
- You want to be able to use the REopt model without incorporating an API call (and associated rate limits).
- You want slightly more flexibility in how you interact with model inputs, optimization parameters, and run types.
- You can install an optimization solver for use with REopt.
- You do not need your results saved in an external database.
- **How do I use the REopt Julia package?:** see instructions [here](https://natlabrockies.github.io/REopt.jl/dev/).
  
**2. When and how to _modify_ the REopt Julia package:**
- You want to make changes to the REopt model beyond modifying input values (e.g., add a new technology).
- You want to suggest a bug fix in the REopt model.
- **How do I modify the REopt Julia package?:** get the (free, open-source) model [here](https://github.com/NatLabRockies/REopt.jl) and see additional instructions [here](https://natlabrockies.github.io/REopt.jl/dev/).
  
**3. When and how to _use_ the REopt_API:**
- You do not want to modify the code or host the API on your own server. 
- You do not want to install or use your own optimization solver (simply POSTing to the REopt API does not require a solver, whereas using the Julia package does).
- You want to be able to access or share results saved in a database using a runuuid.
- **How do I use the REopt API?:** you can access our production version of the API via the [NLR Developer Network](https://developer.nlr.gov/docs/energy-optimization/reopt/). You can view examples of using the API in the [REopt-Analysis-Scripts Repo](https://github.com/NatLabRockies/REopt-Analysis-Scripts/wiki).

**4. When and how to _modify_ the REopt_API:**
- You have made changes to the REopt Julia package that include modified inputs or outputs, and want to reflect those in the REopt API.
- You want to suggest a bug fix in the REopt API or add or modify validation or API endpoints.
- You want to host the API on your own servers.
- **How do I modify the REopt API?:** See this repo's [Wiki](https://github.com/NatLabRockies/REopt_API/wiki) for detailed instructions on installing and developing the API. Also, our [contributing guidelines](https://github.com/NatLabRockies/REopt_API/blob/develop/CONTRIBUTING.md) provide guidelines for suggesting improvements, creating pull requests, and more.
