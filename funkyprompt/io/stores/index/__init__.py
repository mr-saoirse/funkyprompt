import funkyprompt
import json
from funkyprompt.ops.utils import parsing
from funkyprompt.io.stores import VectorDataStore


def update_function_index():
    """
    experimental - we can add an index over functions and stores
    """
    from funkyprompt.io.stores import open_store, list_stores
    from stringcase import titlecase
    from funkyprompt.ops.entities import InstructAbstractVectorStoreEntry
    import json

    stores = [
        open_store(**s).as_function_description(
            f"Set `store_name` argument to {s['namespace']}.{s['name']} - you can use this to search for things related to {titlecase(s['name'])}"
        )
        for s in list_stores()
    ]

    Model = InstructAbstractVectorStoreEntry.create_model(name="FunctionIndex")

    records = []
    for f in stores:
        record = Model(name=f.name, text=json.dumps(f.function_dict()))
        records.append(record)

    store = VectorDataStore(Model).add(records)
    return store


def _summary_helper(texts):
    """
    Pass example texts and get summary and keywords and entities
    """
    # texts = """
    # ['foreshortened by perspective, atop some drawings of itself. Admittedly, the\ntimekeeper looks too large for Harrison to cradle comfortably in his palm, as he\ncould do with the Jefferys watch, which was only half the size of H-4.\nThe reason H-4 is missing from the oil portrait is that Harrison didn’t have it in\nhis possession at the sittings. It was fudged in later, when Harrison’s growing\nfame as “the man who found Longitude” occasioned the creation of the engraving.\nThe intervening events stressed Harrison to the limits of his forbearance.\nAfter the fractious second trial of the Watch in the summer of 1764, the Board\nof Longitude allowed months to pass without saying a word. The commissioners\nwere waiting for the mathematicians to compare their computations of H-4’s\nperformance with the astronomers’ observations of the longitude of Portsmouth\nand Barbados, all of which had to be factored into the judging. When they heard\nthe final report, the commissioners conceded that they were “unanimously of\nopinion that the said timekeeper has kept its time with sufficient correctness.”\nThey could hardly say otherwise: The Watch proved to tell the longitude within\nten miles—three times more accurately than the terms of the Longitude Act\ndemanded! But this stupendous success gained Harrison only a small victory. The\nWatch and its maker still had lots of explaining to do.\nThat autumn, the board offered to hand over \nhalf \nthe reward money, on the\ncondition that Harrison hand over to them all the sea clocks, plus a full disclosure\nof the magnificent clockwork inside H-4. If Harrison expected to receive the \nfull\namount of the £20,000 prize, then he would also have to supervise production of\nnot one but \ntwo \nduplicate copies of H-4—as proof that its design and performance\ncould \nbe duplicated.\nAdding to the tension of these developments, Nathaniel Bliss broke the long\ntradition of longevity associated with the title of astronomer royal. John\nFlamsteed had served in that capacity for forty years, Edmond Halley and James\nBradley had each enjoyed a tenure of more than twenty, but Bliss passed away\nafter just two years at the post. The name of the new astronomer royal—\nand \nex\nofficio member of the Board of Longitude—announced in January 1765, was, as\nHarrison no doubt predicted, his nemesis, Nevil Maskelyne.\nThe thirty-two-year-old Maskelyne took office as fifth astronomer royal on a\nFriday. The very next morning, Saturday, February 9, even before the ceremony\nof kissing the king’s hand, he attended the scheduled meeting of the Board of\nLongitude as its newest commissioner. He listened while the thorny matter of\nHarrison’s payment was further debated. He added his approval to the proposed\nmonetary awards for Leonhard Euler and the widow of Tobias Mayer. Then\nMaskelyne attended to his own agenda.\nHe read aloud a long memorandum extolling the lunar distance method. A\nchorus of four captains from the East India Company, whom he’d brought with\nhim, parroted these sentiments exactly. They had all used the procedure, many\ntimes, they said, just as it was outlined by Maskelyne in \nThe British Mariner’s\nGuide\n, and they always managed to compute their longitude in a matter of a mere\nfour hours. They agreed with Maskelyne that the tables ought to be published and\nwidely distributed, and then “this Method might be easily & generally practiced\nby Seamen.”\nThis marked the beginning of a new groundswell in activity directed at\ninstitutionalizing the lunar distance method. Harrison’s chronometer may have',
    # '9.\nHands on Heaven’s Clock\nThe moving Moon went up the sky,\nAnd no where did abide:\nSoftly she was going up,\nAnd a star or two beside.\n—SAMUEL TAYLOR COLERIDGE\n, “The Rime of the Ancient Mariner”\nT\nhe moving moon, full, gibbous, or crescent-shaped, shone at last for the\nnavigators of the eighteenth century like a luminous hand on the clock of heaven.\nThe broad expanse of sky served as dial for this celestial clock, while the sun, the\nplanets, and the stars painted the numbers on its face.\nA seaman could not read the clock of heaven with a quick glance but only with\ncomplex observing instruments, with combinations of sightings taken together\nand repeated as many as seven times in a row for accuracy’s sake, and with\nlogarithm tables compiled far in advance by human computers for the\nconvenience of sailors on long voyages. It took about four hours to calculate the\ntime from the heavenly dial— when the weather was clear, that is. If clouds\nappeared, the clock hid behind them.\nThe clock of heaven formed John Harrison’s chief competition for the longitude\nprize; the lunar distance method for finding longitude, based on measuring the\nmotions of the moon, constituted the only reasonable alternative to Harrison’s\ntimekeepers. By a grand confluence, Harrison produced his sea clocks at precisely\nthe same period when scientists finally amassed the theories, instruments, and\ninformation needed to make use of the clock of heaven.\nIn longitude determination, a realm of endeavor where nothing had worked for\ncenturies, suddenly two rival approaches of apparently equal merit ran neck and\nneck. Perfection of the two methods blazed parallel trails of development down\nthe decades from the 1730s to the 1760s. Harrison, ever the loner, pursued his\nown quiet course through a maze of clockwork machinery, while his opponents,\nthe professors of astronomy and mathematics, promised the moon to merchants,\nmariners, and Parliament.\nIn 1731, the year after Harrison wrote out the recipe for H-1 in words and\npictures, two inventors—one English, one American—independently created the\nlong-sought instrument upon which the lunar distance method depended. Annals\nof the history of science give equal credit to John Hadley, the country squire who\nfirst demonstrated this instrument to the Royal Society, and Thomas Godfrey, the\nindigent Philadelphia glazier who was struck, almost simultaneously, by the same\ninspiration. (Later it was discovered that Sir Isaac Newton had \nalso \ndrawn plans\nfor a nearly identical device, but the description got lost until long after Newton’s',
    # 'Pepys, who served for a time as an official of the Royal Navy. Commenting on his\n1683 voyage to Tangiers, Pepys wrote: “It is most plain, from the confusion all\nthese people are in, how to make good their reckonings, even each man’s with\nitself, and the nonsensical arguments they would make use of to do it, and\ndisorder they are in about it, that it is by God’s Almighty Providence and great\nchance, and the wideness of the sea, that there are not a great many more\nmisfortunes and ill chances in navigation than there are.”\nThat passage appeared prescient when the disastrous wreck on the Scillies\nscuttled four warships. The 1707 incident, so close to the shipping centers of\nEngland, catapulted the longitude question into the forefront of national affairs.\nThe sudden loss of so many lives, so many ships, and so much honor all at once,\non top of centuries of previous privation, underscored the folly of ocean\nnavigation without a means for finding longitude. The souls of Sir Clowdisley’s\nlost sailors— another two thousand martyrs to the cause—precipitated the famed\nLongitude Act of 1714, in which Parliament promised a prize of £20,000 for a\nsolution to the longitude problem.\nIn 1736, an unknown clockmaker named John Harrison carried a promising\npossibility on a trial voyage to Lisbon aboard H.M.S. \nCenturion\n. The ship’s officers\nsaw firsthand how Harrison’s clock could improve their reckoning. Indeed, they\nthanked Harrison when his newfangled contraption showed them to be about\nsixty miles off course on the way home to London.\nBy September 1740, however, when the \nCenturion \nset sail for the South Pacific\nunder the command of Commodore George Anson, the longitude clock stood on\nterra firma in Harrison’s house at Red Lion Square. There the inventor, having\nalready completed an improved second version of it, was hard at work on a third\nwith further refinements. But such devices were not yet generally accepted, and\nwould not become generally available for another fifty years. So Anson’s squadron\ntook the Atlantic the old-fashioned way, on the strength of latitude readings, dead\nreckoning, and good seamanship. The fleet reached Patagonia intact, after an\nunusually long crossing, but then a grand tragedy unfolded, founded on the loss\nof their longitude at sea.\nOn March 7, 1741, with the holds already stinking of scurvy, Anson sailed the\nCenturion \nthrough the Straits Le Maire, from the Atlantic into the Pacific Ocean.\nAs he rounded the tip of Cape Horn, a storm blew up from the west. It shredded\nthe sails and pitched the ship so violently that men who lost their holds were\ndashed to death. The storm abated from time to time only to regather its strength,\nand punished the \nCenturion \nfor fifty-eight days without mercy. The winds carried\nrain, sleet, and snow. And scurvy all the while whittled away at the crew, killing\nsix to ten men every day.\nAnson held west against this onslaught, more or less along the parallel at sixty\ndegrees south latitude, until he figured he had gone a full two hundred miles\nwestward, beyond Tierra del Fuego. The other five ships of his squadron had been\nseparated from the \nCenturion \nin the storm, and some of them were lost forever.\nOn the first moonlit night he had seen in two months, Anson at last anticipated\ncalm waters, and steered north for the earthly paradise called Juan Fernández\nIsland. There he knew he would find fresh water for his men, to soothe the dying\nand sustain the living. Until then, they would have to survive on hope alone, for\nseveral days of sailing on the vast Pacific still separated them from the island',
    # 'oasis. But as the haze cleared, Anson sighted \nland \nright away, dead ahead. It was\nCape Noir, at the western edge of Tierra del Fuego.\nHow could this have happened? Had they been sailing in reverse?\nThe fierce currents had thwarted Anson. All the time he thought he was gaining\nwestward, he had been virtually treading water. So he had no choice but to head\nwest \nagain\n, then north toward salvation. He knew that if he failed, and if the\nsailors continued dying at the same rate, there wouldn’t be enough hands left to\nman the rigging.\nAccording to the ship’s log, on May 24, 1741, Anson at last delivered the\nCenturion \nto the latitude of Juan Fernandez Island, at thirty-five degrees south. All\nthat remained to do was to run down the parallel to make harbor. But which way\nshould he go? Did the island lie to the east or to the west of the \nCenturion’\ns\npresent position?\nThat was anybody’s guess.\nAnson guessed west, and so headed in that direction. Four more desperate days\nat sea, however, stripped him of the courage of his conviction, and he turned the\nship around.\nForty-eight hours after the \nCenturion \nbegan beating east along the thirty-fifth\nparallel, land was sighted! But it showed itself to be the impermeable, Spanish-\nruled, mountain-walled coast of Chile. This jolt required a one-hundred-eighty-\ndegree change in direction, and in Anson’s thinking. He was forced to confess that\nhe had probably been within hours of Juan Fernandez Island when he abandoned\nwest for east. Once again, the ship had to retrace her course.\nOn June 9, 1741, the \nCenturion \ndropped anchor at last at Juan Fernandez. The\ntwo weeks of zigzag searching for the island had cost Anson an additional eighty\nlives. Although he was an able navigator who could keep his ship at her proper\ndepth and protect his crew from mass drowning, his delays had given scurvy the\nupper hand. Anson helped carry the hammocks of sick sailors ashore, then\nwatched helplessly as the scourge picked off his men one by one . . . by one by\none, until more than half of the original five hundred were dead and gone.',
    # 'the routine work to various craftsmen and did only the difficult parts, especially\nthe meticulous adjusting, himself.\nAs Arnold’s star rose, the word \nchronometer \ncame into general usage as the\npreferred name for a marine timekeeper. Jeremy Thacker had coined this term in\n1714, but it didn’t catch on until 1779, when it appeared in the title of a\npamphlet by Alexander Dalrymple of the East India Company, \nSome Notes Useful\nto Those Who Have Chronometers at Sea\n.\n“The machine used for measuring time at sea is here named chronometer,”\nDalrymple explained, “[as] so valuable a machine deserves to be known by a\nname instead of a definition.”\nArnold’s first three box chronometers, which he supplied to the Board of\nLongitude, traveled, as did K-1, with Captain Cook. The whole Arnold trio sailed\non the 1772-75 voyage to the Antarctic and the South Pacific. The “vicissitudes of\nclimates,” as Cook described the global weather range, caused Arnold’s clocks to\ngo poorly. Cook declared himself unimpressed with the way they performed\naboard his two ships.\nThe board cut off Arnold’s funding as a result. But this action, instead of\ndiscouraging the young watchmaker, spurred him on to new concepts, all of\nwhich he patented and perpetually improved. In 1779 he created a sensation with\na pocket chronometer, called No. 36. It truly was small enough to be worn in the\npocket, and Maskelyne and his deputies carried it in theirs for thirteen months to\ntest its accuracy. From one day to the next, it never gained or lost more than\nthree seconds.\nMeanwhile, Arnold continued to hone his skill at mass production. He opened a\nfactory at Well Hall, south London, in 1785. His competitor, Thomas Mudge Jr.,\ntried to run a factory, too, turning out some thirty imitations of his father’s\nchronometers. But Thomas Jr. was a lawyer, not a clockmaker. No timekeeper\nthat came from the junior Mudge works ever matched the accuracy of the elder’s\nthree originals. And yet, a Mudge chronometer cost twice as much as one of\nArnold’s.\nArnold did everything methodically. He established his reputation in his early\ntwenties by making a marvelous miniature watch, only half an inch in diameter,\nwhich he mounted in a finger ring and presented to King George III as a gift in\n1764. Arnold married \nafter \nhe had laid out his lifework as a maker of marine\ntimekeepers. He chose a wife who was not only well-to-do but also well prepared\nto improve his business as well as his home life. Together they invested their all\nin their only child, John Roger Arnold, who also tried to further the family\nenterprise. John Roger studied watchmaking in Paris under the finest teachers of\nhis father’s choosing, and when he became full partner in 1784, the company\nname changed to Arnold and Son. But Arnold Sr. always remained the better\nwatchmaker of the two. His brain bubbled over with myriad ways to do things,\nand he seems to have tried them all in his chronometers. Most of his best\nmousetraps were artful simplifications of things Harrison had pioneered in a\nclever but complicated way.\nArnold’s biggest competition came from Thomas Earnshaw, who ushered in the\nage of the truly modern chronometer. Earnshaw reduced Harrison’s complexity\nand Arnold’s prolificacy to an almost platonic essence of chronometer. Equally\nimportant, he brought one of Harrison’s biggest ideas down to small scale at last,']"""

    act = f"""Please provide a summary of the text in a couple of paragraphs. 
        Also 
        - list any Full Names mentioned (you should simply omit partial names) and 
        - list of non-name key categories or topics that describe the summary using recognizable ontological categories
        You should provide the response in json format with attributes `summary`, 'entity_refs`, 'keywords'
        TEXT:
        ```
        {texts}
        ```
        """
    data = funkyprompt.agent.ask(act)
    # parse directly or indirectly
    try:
        return json.loads(data)
    except:
        return parsing.parse_fenced_code_blocks(data, select_type="json")[0]


def add_cluster_summaries(
    store: VectorDataStore, sample_size=5, plot_clusters=True, **kwargs
):
    """
    For a given store, we cluster using parameters and then summarize N neighbours and re-save a node ad d=-1 with type == summary
    we update the story to filter by level or type so that we can probe a store
    the summary should embed graph edges to related texts

    extend the schema used in the store to have labels (keywords) and entity refs lust as columns - when asking for a summary use the structure; summary, entity_ref keywords
    """

    import numpy as np
    import umap
    import umap.plot
    import polars as pl
    import hdbscan

    # import plotly.express as px

    df = store.load()[["name", "text", "doc_id", "vector", "id"]]

    v = np.stack(df["vector"].to_list())
    funkyprompt.logger.debug(f"Fitting data...")
    emb = pl.DataFrame(
        umap.UMAP().fit(v).embedding_, schema={"x": pl.Float32, "y": pl.Float32()}
    )

    clusterer = hdbscan.HDBSCAN(min_cluster_size=10, gen_min_span_tree=True)
    c = clusterer.fit_predict(emb[["x", "y"]].to_numpy())
    emb = emb.with_columns(pl.Series(name="cluster", values=c))
    df = df.hstack(emb)

    Model = store._entity
    cluster_ids = [cid for cid in df["cluster"].unique() if cid != -1]
    records = []
    funkyprompt.logger.debug(f"Adding summaries to store")
    for c in cluster_ids:
        texts = df.filter(pl.col("cluster") == c).sample(sample_size)["text"].to_list()
        texts = "\n".join([t for t in texts if t])
        # here we take a summary of the N delegate samples - one per cluster
        cluster_summary = funkyprompt.agent.summarize(
            "Provide a two paragraph summary of the ideas in the text", data=texts
        )

        funkyprompt.logger.debug(cluster_summary)
        # create a record from the summary
        record = Model(
            name=f"summary_{c}",
            depth=-1,
            text=cluster_summary.get("summarized_response"),
            doc_id="cluster_summaries",
        )
        records.append(record)

    funkyprompt.logger.debug(f"Adding {len(records)} samples")

    store.add(records)

    if plot_clusters:
        import plotly.express as px

        px.scatter(x=df["x"], y=df["y"], color=df["cluster"])
    return df
    # find centers / sample from the clusters
