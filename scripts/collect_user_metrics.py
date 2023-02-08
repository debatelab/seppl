# %% 

from google.cloud import firestore
import uuid
import unidecode
import os
import logging
import datetime
import secrets
import string
import time
import tqdm
import pandas as pd
import ast

# %%
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Ready to log")

# %%
os.chdir("..")
db = firestore.Client.from_service_account_json("seppl-deepa2-firebase-key.json")



# %%

########################
# GET CANDIES PER USER #
########################

kit_ars1_ws2223 = pd.read_csv("kit_ars1_ws2223_with_email.csv")
kit_ars1_ws2223


# %%

def get_candies_per_user(username):
    user_ref = db.collection(f"users").document(username)
    user = user_ref.get().to_dict()
    return user.get("sofa_counter", 0)

get_candies_per_user("marcantonio-galuppi")

# %%

kit_ars1_ws2223["candies"] = kit_ars1_ws2223["username"].apply(get_candies_per_user)
kit_ars1_ws2223
# %%

kit_ars1_ws2223.to_csv("kit_ars1_ws2223_candies_jan01.csv", index=False)


# %%

#######################
# GET MEDALS PER USER #
#######################

def get_max_medals_in_project(user_id, project_id, timestamp="2022"):
    metrics_ref = db.collection(u'metrics')
    n_medals = 3
    while n_medals > 0: 
        project_metrics_query = metrics_ref.where(
            u'user_id', u'==', user_id).where(
                u'project_id', u'==', project_id)
        project_metrics_query = project_metrics_query.where(
            u'reconstruction_phase', u'==', n_medals)
        project_metrics_query = project_metrics_query.where(
            u'timestamp', u'>=', timestamp).limit(1)
        try:
            metric_doc = next(project_metrics_query.stream())
            return n_medals
        except Exception:
            pass
        n_medals -= 1

    return n_medals

get_max_medals_in_project("marcantonio-galuppi",
"Week1-1-ShouldAbortionBeLegal",timestamp="2022-10-01")

# %%


get_max_medals_in_project("marcantonio-galuppi",
"Week1-0-ShouldTabletsReplaceTextboo", timestamp="2023-01-01")
# %%

def get_projects(user_id):
    project_ids = []
    user_ref = db.collection(u"users").document(user_id)
    projects = user_ref.collection(u"projects").stream()
    for project in projects:
        project_ids.append(project.id)
    return project_ids
# %%

get_projects("marcantonio-gagliardi")

# %%

def get_max_medals(
    user_id,
    project_ids,
    from_week=9,
    to_week=20,
    timestamp="2022-01-01"
):
    medals_total = 0
    logger.info("project_ids: %s", project_ids)
    for project_id in project_ids:
        if any(
            project_id.startswith(f"Week{week}-")
            for week in range(from_week, to_week+1)
        ):
            logger.info("Getting max medals for project: %s (of %s)", project_id, user_id)
            max_medals = get_max_medals_in_project(
                user_id,
                project_id,
                timestamp=timestamp
            )
            medals_total += max_medals
    return medals_total

# %%

#projects_bova = get_projects("licia-bova")
get_max_medals(
    "ilaria-pelli",
    ['Week1-0-KneelingduringtheNationalA', 'Week1-1-ShouldthePennyStayinCircu', 'Week1-2-WasRonaldReaganaGoodPresi', 'Week1-3-ShouldTeachersGetTenure', 'Week1-4-ShouldTabletsReplaceTextboo', 'Week10-1-Communitysentencing', 'Week10-2-Fairtradeweshouldnotsuppo', 'Week10-3-Fairtradeweshouldnotsuppo', 'Week10-4-EnglishParliament', 'Week10-5-Examinationsabolitionof', 'Week11-1-Nationalidentitycards', 'Week11-2-HouseofLordselectedvapp', 'Week11-3-Marxism', 'Week11-4-Monarchyabolitionof', 'Week11-5-InternationalCriminalCourt', 'Week12-1-Politicalcorrectness', 'Week12-2-Privacyofpublicfigures', 'Week12-3-Prisonersrighttovotedeni', 'Week12-4-Organdonationpriorityforh', 'Week12-5-Privatemilitarycorporations', 'Week13-1-Schooluniform', 'Week13-2-Sizezeromodelsbanningof', 'Week13-3-Schoolsportcompulsory', 'Week13-4-Socialcontractexistenceof', 'Week13-5-ShouldBritainleavetheEU', 'Week15-0-UnitedNationsfailureofthe', 'Week15-1-Universityeducationfreefor', 'Week15-2-Veilprohibitionofthe', 'Week15-3-UnitedNationsstandingarmy', 'Week15-4-Terroristsnegotiationwith', 'Week2-0-DoStandardizedTestsImprove', 'Week2-1-ShouldRecreationalMarijuana', 'Week2-2-ShouldtheUnitedStatesMaint', 'Week2-3-ShouldMoreGunControlLawsB', 'Week2-4-SaturdayHalloweenProsCo', 'Week3-0-OlympicsHostingProsCons', 'Week3-1-ShouldMoreGunControlLawsB', 'Week3-2-WasBillClintonaGoodPresid', 'Week3-3-ShouldRecreationalMarijuana', 'Week3-4-ShouldtheUnitedStatesConti', 'Week4-0-ShouldtheFederalMinimumWag', 'Week4-1-ShouldPitBullsBeBannedTo', 'Week4-2-BannedBooksProsandConsT', 'Week4-3-ShouldtheFederalMinimumWag', 'Week4-4-KneelingduringtheNationalA', 'Week5-0-ShouldtheUnitedStatesMaint', 'Week5-1-DakotaAccessPipelineProsan', 'Week5-2-StudentLoanDebtElimination', 'Week5-3-MandatoryNationalServiceP', 'Week5-4-OlympicsHostingProsCons', 'Week6-0-DefundingthePoliceProsand', 'Week6-1-ShouldtheUnitedStatesMaint', 'Week6-2-SchoolVouchersProsCons', 'Week6-3-IsaCollegeEducationWorthI', 'Week6-4-MandatoryNationalServiceP', 'Week7-0-ShouldBirthControlPillsBe', 'Week7-1-WasBillClintonaGoodPresid', 'Week7-2-GMOProsandConsShouldGen', 'Week7-3-IsCellPhoneRadiationSafe', 'Week7-4-InternetStupidityPros', 'Week8-0-PokemonGoProsConsPro', 'Week8-1-DefundingthePoliceProsand', 'Week8-2-ShouldChurchesIncludingMos', 'Week8-3-IsSocialMediaGoodforSocie', 'Week8-4-CancelCultureTop3Prosand', 'Week9-0-Artsfundingbythestateabo', 'Week9-1-CapitalismvSocialism', 'Week9-2-Abortionondemand', 'Week9-3-BBCprivatisationof', 'Week9-4-Beautycontestsbanningof'],
    from_week=1, 
    to_week=8,
    #timestamp="2022-01-01"
)

# %%
#kit_ars1_ws2223 = pd.read_csv("kit_ars1_ws2223_with_email.csv")
#kit_ars1_ws2223_active = kit_ars1_ws2223[~kit_ars1_ws2223["email"].isna()]
kit_ars1_ws2223_active = pd.read_csv(
    "kit_ars1_ws2223_medals_230207.csv",
    converters={'projects': pd.eval}
)
kit_ars1_ws2223_active
# %%
kit_ars1_ws2223_active.drop(columns=["medals_w1_w8","medals_w9_w20"], inplace=True)
kit_ars1_ws2223_active
# %%
#kit_ars1_ws2223_active["projects"] = kit_ars1_ws2223_active["username"].apply(get_projects)
#kit_ars1_ws2223_active
# %%
medals_w1_w8 = []
medals_w9_w20 = []
for username, projects in tqdm.tqdm(zip(
    kit_ars1_ws2223_active["username"].to_list(),
    kit_ars1_ws2223_active["projects"].to_list(),
)):
    #logger.info(f"Getting medals for {username} with projects: {projects}.")
    #time.sleep(.1)
    medals_w1_w8.append(get_max_medals(username, projects, from_week=1, to_week=8))
    medals_w9_w20.append(get_max_medals(username, projects, from_week=9, to_week=20))
# %%
kit_ars1_ws2223_active["medals_w1_w8"] = medals_w1_w8
# %%
kit_ars1_ws2223_active["medals_w9_w20"] = medals_w9_w20
# %%
kit_ars1_ws2223_active
# %%
kit_ars1_ws2223_active.to_csv("kit_ars1_ws2223_medals_230208.csv", index=False)

# %%
set(medals_w1_w8)
# %%
