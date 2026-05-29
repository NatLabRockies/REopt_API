# Contributing to REopt
Thank you for contributing! 

Below are guidelines for making contributions to REopt.


### I don't want to read this whole thing I just have a question!!!
Please do not create an "issue" if you have a question. You might find answers to general questions on our [REopt-API-Analysis Discussion Board](https://github.com/NatLabRockies/REopt-API-Analysis/discussions/) or [our web site](https://www.nlr.gov/reopt/) and you can reach us at [reopt@nlr.gov](mailto:reopt@nlr.gov). 

## How Can I Contribute?

#### Reporting Bugs
Please create an [issue](https://github.com/NatLabRockies/REopt_API/issues) for a bug that you have encountered. (The issue template provides more guidance.)


#### Suggesting Enhancements
Please refer to the instructions in the issue template provided in the [issues](https://github.com/NatLabRockies/reopt_api/issues) tab for suggesting enhancements. 

Note that not all suggestions will be integrated into the public code. Enhancments should provide a clear benefit to the community of REopt API users as well as preserve backwards compatibility (in most cases). Lastly, NLR developer time is limited so we can not create every suggested enhancement.

#### Pull Requests

##### I have created a bug fix
Besides creating an issue for bugs found in the code, you can help the community by creating a suggested fix for a bug that you have found. Here are the general steps for contributing your bug-fix:
- First, fork the repository and create a new branch on your fork with a name like "fix_some_bug"
- Once the bug is fixed, run the full test suite (instructions for running the test suite are available [here](https://github.com/NatLabRockies/reopt_api/wiki/Testing-the-REopt-API))
- If it passes, send a PR to the original repository. If you haven't signed the [Code License Agreement](https://github.com/NatLabRockies/REopt_API/blob/master/cla.md) already, the CLA Assistant will comment on your PR and request you to sign the CLA. You can simply comment "I have read the CLA Document and I hereby sign the CLA" to sign the [CLA](https://github.com/NatLabRockies/REopt_API/blob/master/cla.md). 
- If tests aren't passing, then first look the specific test[s] that is/are failing. Then think through - "do I expect the test to fail after introducing the bug-fix I am proposing?"
    - If yes, then please provide a clear description of the identified bug, how you fixed it, and explanation for why the fix is making an existing test fail
    - If no, then revisit the changes you introduced to identify where the problem is

##### I have added a feature that other users will benefit from
Not all features or Pull Requests will be merged into the public code. New features must provide clear benefit for the user community, as well as ideally preserve backwards compatibility.

The following describes the general steps for adding a feature to the REopt API:
- First fork the repository and create a new branch on your fork
- Then develop the feature on that branch (a detailed tutorial for REopt-api feature development is [here](https://github.com/NatLabRockies/reopt_api/wiki/Developing-the-API))
- Note that we highly recommend test-driven development
- After the feature is complete, run the full test suite
- If it passes, send a PR to the original repository. If you haven't signed the [Code License Agreement](https://github.com/NatLabRockies/REopt_API/blob/master/cla.md) already, the CLA Assistant will comment on your PR and request you to sign the CLA. You can simply comment "I have read the CLA Document and I hereby sign the CLA" to sign the [CLA](https://github.com/NatLabRockies/REopt_API/blob/master/cla.md). 
- If tests aren't passing, then first look the specific test which is failing. Then think through - Do I expect this test to fail after having added the new feature? 
    - If yes, then please provide a clear explanation for why the existing test[s] should fail after the introduction of the new feature
    - If no, then revisit the new feature you have developed to troubleshoot the problem with the failing test[s]


## Recommended IDE
- We recommend using PyCharm to keep the file formatting consistent across platforms. PyCharm has a free community edition.

## Git Commit Messages
- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
