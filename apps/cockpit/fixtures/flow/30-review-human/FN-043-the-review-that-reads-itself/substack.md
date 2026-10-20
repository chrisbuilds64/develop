# The review that reads itself

Last month I let an agent review its own output for a week. It went well, which is the problem.

Every morning the pipeline produced a draft, and every morning the same agent checked the draft against the same rules it had just written it by. The checks passed. The log was green. I read three of the drafts anyway, because reading is the only part of the job I do not trust a tool with, and two of them contained a claim that was simply wrong. Not dangerous, not even embarrassing. Wrong in a way that only someone who had been in the room would notice.

The review had not failed. It had done exactly what it was built to do: confirm that the output was consistent with itself. A check that shares its author with the thing it checks cannot be surprised. It has the same blind spots, the same habits, the same idea of what a good paragraph looks like.

So I changed one thing. The agent still drafts, and a second pass still checks form: length, structure, the rules we wrote down. But the question "is this true" now goes to a person, and the pipeline cannot move the piece forward until that person has written one line into the review file. Not a click. A line, with a name on it.

This costs me about ten minutes per piece. I expected to resent it. Instead the review file became the most useful document in the folder. It shows what the agent got wrong, how often, and in which direction. After three weeks the pattern was obvious: the agent rounds numbers toward the story it is telling. It never invents a figure. It nudges a real one.

None of that would have shown up in a pass rate.

The lesson I take from this is narrow, and I would rather keep it narrow. Automated review is good at consistency and bad at truth, and the two feel identical from the outside. If your pipeline reports that everything passed, ask who wrote the thing that checked it. If the answer is the same system, you have measured agreement, not quality.

What I do now is simple. Form is checked by a machine. Facts are checked by a person. The handover between them is a file, so it can be read later by anyone who wants to know why a piece went out.

It is slower than the green log. It is also the only version of this week I would defend in front of a client.

Next time: what the review file looks like after a hundred pieces, and which of my rules turned out to be decoration.
