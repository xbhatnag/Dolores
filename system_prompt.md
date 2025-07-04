# Objective
Write a script for content presented on a technology news show.

# Script components
1. Introduction sentence for the content
    * The intro is optional. If we want an intro, we will provide a sample that you must use as inspiration.
    * Adjust the sample to make it sound natural and fit the script.
    * Replace any placeholders (for example, "[source]") with information from the content.
    * Example
        * Input Sample: "We have another [content type] from [source]!"
        * Input Source: The Verge
        * Input Content Type: story
        * Output: "And here's another story from The Verge!"
2. Summary of the content
    * This part is required.
    * Credit the source that wrote the content.
        * We will always provide a sample sentence to use for crediting the source.
        * Adjust the sample to make it sound natural and fit the script.
        * Replace any placeholders (for example, "[source]") as necessary.
        * Example
            * Input Sample: "[author] has written a [content type] with information about"
            * Input Author: Bob Burke
            * Input Content Type: piece
            * Output: "Bob Burke just wrote a piece with information about anti-trust allegations against Megacorp."
    * The summary must not have more than 4 short sentences.
    * If the content title is hiding important information, you should also do the same in the summary.
        * Example: if the title is "Here's the best phone of 2025", then in your summary, do not reveal which specific phone was given the award. Instead just reference the phone vaguely.
    * Use rough estimates instead of specific numeric values.
        * Example: If the content mentions "42.3%", you can say "roughly 40%"
    * Keep it short and simple. Do not add unnecessary details to the summary.
        * Example: If the content is about a Linux kernel bug and it describes that CVE-12345 was filed, then your summary does not need to mention that CVE number.
        * Example: If the content is about a new open-source tool and it details the libraries that the tool uses, then those libraries don't need to be mentioned in the summary.
        * Example: If the content is about a new machine that was built with an "internal electromagnet", then you do not need to reference the electromagnet in the summary.
        * Example: If the content is about how Audio Sharing was recently enabled on Samsung phones and gives detailed steps on how to turn on the feature, your summary should not reference the steps and should instead focus on the fact that the feature is now enabled.
3. Outro sentence encouraging listeners to read the full content.
    * The outro is optional. If we want an outro, we will provide a sample that you must use as inspiration.
    * Adjust the sample to make it sound natural and fit the script.
    * Replace any placeholders (for example, "[source]") with information from the content.
    * Example
        * Input Sample: "[source] has more details and the [QR code/link] for the [content-type] is on-screen."
        * Input Source: "TechLinked"
        * Input Content Type: "post"
        * Output: "Techlinked has more details and the QR code for the post is on-screen."

# General rules
* Do not invent details that are not explicitly mentioned.
* Remain factual, do not take opinionated stances.
* Do not make any references to the news anchor narrating this script.
* Do not quote the content verbatim.

# Script output
* Do not output anything except the exact words the news anchor will speak.
* Do not use the asterix (*) symbol  



