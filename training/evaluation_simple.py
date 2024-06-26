"""Evaluate the rule-based or transformer-based parser on the human annotated parsing data. No synthetic modifications
are introduced.
"""
import os
import pandas as pd
import numpy as np
import krippendorff
from statsmodels.stats.inter_rater import fleiss_kappa

def logf(fw, msg=""):
    """Write message to both fw and stdout"""
    print(msg)
    fw.write(msg + "\n")

def evaluate(annotator_1_file, annotator_2_file, annotator_3_file, parsed_screenplays_folder, 
                    screenplays_line_numbers_file, results_dir, trx=False):
    """Calculate interrater reliability scores and performance of the rule-based (trx=False) or transformer-based 
    parser (trx=True) parser against the human-annotated data without any synthetic modifications. The parser is never
    run and only precomputed parse outputs are read.

    Args:
        annotator_1_file: annotator 1's excel file
        annotator_2_file: annotator 2's excel file
        annotator_3_file: annotator 3's excel file
        parsed_screenplays_folder: directory containing parsed (output of parsing with the rule-based and 
            transformer-based parser) and original screenplays
        screenplays_line_numbers_file: text file containing the line number offsets of the script excerpts from the
            full-length screenplay which was human annotated
        results_dir: directory where the result of the evaluation will be saved
        trx: evaluate the transformer-based parser instead of the default rule-based parser
    """

    parser_type = "trx" if trx else "rule"
    output_file = open(os.path.join(results_dir, f"evaluation_simple/{parser_type}.txt"), "w")

    if trx:
        parsed_screenplays_folder = os.path.join(parsed_screenplays_folder, "parsed-robust-screenplays")
    else:
        parsed_screenplays_folder = os.path.join(parsed_screenplays_folder, "parsed-screenplays")


    #####################################################################
    #### read annotator excel files
    #####################################################################

    print("reading annotator 1 file...")
    annotator_1_df_dict = pd.read_excel(annotator_1_file, sheet_name=None, header=1, 
                                        usecols=["line","S","N","C","D","E","T","M"])

    print("reading annotator 2 file...")
    annotator_2_df_dict = pd.read_excel(annotator_2_file, sheet_name=None, header=1, 
                                        usecols=["line","S","N","C","D","E","T","M"])

    print("reading annotator 3 file...")
    annotator_3_df_dict = pd.read_excel(annotator_3_file, sheet_name=None, header=1, 
                                        usecols=["line","S","N","C","D","E","T","M"])

    line_numbers = open(screenplays_line_numbers_file).read().splitlines()

    #####################################################################
    #### find annotations of each rater and save them to "ann" dictionary
    #####################################################################

    movies = list(annotator_1_df_dict.keys())[1:]
    ann = {}

    for movie in movies:
        ann[movie] = {}
        
        for i, df in enumerate([annotator_1_df_dict[movie], annotator_2_df_dict[movie], annotator_3_df_dict[movie]]):
            anns = []

            for _, row in df.iterrows():
                if not isinstance(row["line"], str) or (isinstance(row["line"], str) and row["line"].strip() == ""):
                    anns.append("O")
                else:
                    n = 0
                    atag = ""
                    for tag in ["S","N","C","D","E","T"]:
                        if isinstance(row[tag], str) and row["line"].strip() == row[tag].strip():
                            atag = tag
                        else:
                            n += 1
                    if atag != "" and n == 5:
                        anns.append(atag)
                    else:
                        anns.append("O")
            
            ann[movie]["ann{}".format(i + 1)] = anns

    #####################################################################
    #### print interrater reliability
    #####################################################################

    n_rater_pairs = 0
    n_agree_rater_pairs = 0
    item_x_class_table = np.zeros((sum(len(annotator_1_df_dict[movie]) for movie in movies), 7), dtype=int)
    i = 0

    logf(output_file, "agreement scores by movie:")

    for movie in movies:
        n1, n2, n3 = 0, 0, 0
        
        for a1, a2, a3 in zip(ann[movie]["ann1"], ann[movie]["ann2"], ann[movie]["ann3"]):
            S = set([a1, a2, a3])
            if len(S) == 1:
                n1 += 1
                n_agree_rater_pairs += 3
            elif len(S) == 2:
                n2 += 1
                n_agree_rater_pairs += 1
            else:
                n3 += 1
            n_rater_pairs += 3
            
            for a in [a1, a2, a3]:
                j = ["S","N","C","D","E","T","O"].index(a)
                item_x_class_table[i, j] += 1
            i += 1
        
        n = n1 + n2 + n3
        logf(output_file, "\t{:35s} {:5.1f}% all agree, {:3d} two agree, {:3d} all disagree".format(
            movie, 100*n1/n, n2, n3))

    logf(output_file, )

    ka = krippendorff.alpha(value_counts=item_x_class_table)
    fk = fleiss_kappa(item_x_class_table, method="fleiss")

    logf(output_file, )
    logf(output_file, "interrater reliability scores:")
    logf(output_file, "\t{:5.1f}% rater pairs agree".format(100*n_agree_rater_pairs/n_rater_pairs))
    logf(output_file, "\t{:.4f} fleiss kappa".format(fk))
    logf(output_file, "\t{:.4f} krippendorff alpha".format(ka))
    logf(output_file, )

    #####################################################################
    #### find majority annotation and system prediction, and save to "ann" dictionary
    #####################################################################

    for movie in ann.keys():
        maj = []
        for a1, a2, a3 in zip(ann[movie]["ann1"], ann[movie]["ann2"], ann[movie]["ann3"]):
            if a1 == a2 or a1 == a3:
                maj.append(a1)
            elif a2 == a3:
                maj.append(a2)
            else:
                maj.append("O")
        ann[movie]["maj"] = maj

    for line in line_numbers:
        movie, _, i, j = line.split()
        i, j = int(i), int(j)
        tags = open(os.path.join(parsed_screenplays_folder, movie + "_tags.txt")).read().splitlines()
        tags = [t if t in ["S","N","C","D","E","T"] else "O" for t in tags]
        ann[movie]["sys"] = tags[i:j]

    #####################################################################
    #### print accuracy of parser by movie
    #####################################################################

    logf(output_file, "parser accuracy by movie:")

    for movie in ann.keys():
        n = sum(x == y for x, y in zip(ann[movie]["maj"], ann[movie]["sys"]))
        N = len(ann[movie]["maj"])
        logf(output_file, "\t{:35s} acc = {:5.1f}%".format(movie, 100*n/N))
    logf(output_file, )

    #####################################################################
    #### print precision, recall and f1 by tag
    #####################################################################

    logf(output_file, "parser precision, recall, and F1 by tag:")

    for tag in ["S","N","C","D","E","T"]:
        tp, fp, fn = 0, 0, 0
        for movie in ann.keys():
            tp += sum(x == y == tag for x, y in zip(ann[movie]["maj"], ann[movie]["sys"]))
            fp += sum(x != y == tag for x, y in zip(ann[movie]["maj"], ann[movie]["sys"]))
            fn += sum(tag == x != y for x, y in zip(ann[movie]["maj"], ann[movie]["sys"]))
        p = tp/(tp + fp)
        r = tp/(tp + fn)
        f1 = 2*p*r/(p + r)
        logf(output_file, "\t{}: p = {:4.1f}, r = {:4.1f}, f1 = {:4.1f}".format(tag, 100*p, 100*r, 100*f1))
    
    output_file.close()