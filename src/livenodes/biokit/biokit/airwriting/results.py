import argparse
import collections
from . import db
from sqlalchemy.sql import func
import align
import json

class ResultHandler:
    def __init__(self, session):
        """
        Initialize a result handler with a database session
        
        Keyword arguments:
        session - SQLAlchemy session object
        """
        self.session = session

    def get_cv_result(self, cv_id, iteration = None):
        """
        Retrieve cross validation results from database
        
        Keyword arguments:
        cv_id - id of the cross validation
        iteration - if given, retrieve result only for this training iteration
        
        Returns:
        
        """
        query = self.session.query(db.CrossValidation,
                                  db.Configuration,
                                  db.Result,
                                  db.Job,
                                  db.Result.iteration,
                                  func.count(db.Result.id),
                                  func.avg(db.Result.ter),
                                  func.avg(db.Job.cputime)
                                  ).\
                                  join(db.CrossValidation.configurations).\
                                  join(db.Result).\
                                  join(db.Job).\
                                  filter(db.CrossValidation.id == cv_id).\
                                  group_by(db.Result.iteration)
        if iteration:
            return query.filter(db.Results.iteration == iteration).one()
        else:
            return query.all()

    def get_cv_detail(self, cv_id, iteration = None):
        """
        Retrieve cross validation results from database by fold

        Arguments:
        cv_id - id of the db.CrossValidation
        iteraton - if given, retrieve results only for this iteration
        """
        query = self.session.query(db.CrossValidation,
                                  db.Configuration,
                                  db.Result,
                                  db.Job,
                                  db.Result.iteration,
                                  db.Result.ter,
                                  db.Job.cputime
                                  ).\
                                  join(db.CrossValidation.configurations).\
                                  join(db.Result).\
                                  join(db.Job).\
                                  filter(db.CrossValidation.id == cv_id)
        #                          group_by(db.Result.iteration)
        if iteration:
            result =  query.filter(db.Results.iteration == iteration).one()
        else:
            result =  query.all()
        resdict = self.get_cvresults(result)
        return resdict


    def get_cv_overview(self):
        """
        Get an overview over all cv results
        """
        cvs = self.session.query(db.CrossValidation).all()
        cvresults = []
        for cv in cvs:
            cvresults.extend(self.get_cv_result(cv.id))
        ov = self.get_cvresults(cvresults)
        return(ov)

    def get_cvresults(self, cvresults):
        config_keys = ("basemodel_id", "id" ) 
        biokit_keys = ('token_insertion_penalty', 'languagemodel_weight',
                       'hypo_topn', 'hypo_beam',
                       'final_hypo_beam', 'final_hypo_topn',
                       'lattice_beam')
        ibis_keys = ('wordPen', 'lz', 'wordBeam', 'stateBeam', 'morphBeam')
        #get all cross validations
        ov = []
        for result in cvresults:
            d = collections.OrderedDict()
            if len(result) == 8:
                crossval, config, result, job, iteration, count, ter, cputime = result
                d['crossval_id'] = crossval.id
                d['count'] = count
            elif len(result) == 7:
                crossval, config, result, job, iteration, ter, cputime = result
                d['crossval_id'] = crossval.id
                d['exp_id'] = config.testset.recordings[0].experiment.string_id
            else:
                raise Exception("unknown length of result %s: %s" % (len(result), result))
            for key in config_keys:
                d[key] = getattr(config, key)
            for key in biokit_keys:
                try:
                    d[key] = getattr(config.biokitconfig, key)
                except AttributeError:
                    d[key] = None
            for key in ibis_keys:
                try:
                    d[key] = getattr(config.ibisconfig, key)
                except AttributeError:
                    d[key] = None
            d['iteration'] = iteration
            d['ter'] = ter
            resultlist = json.loads(result.resultlist[0].resjson)
            cer = computeCharacterErrorRate(resultlist)
            d['cer'] = cer
            d['cputime'] = cputime
            if cputime is not None:
                d['rt factor'] = cputime*9./config.iterations/(236*60)
            else:
                d['rt factor'] = None
            ov.append(d)
        return(ov)

def insertblanks(s):
    """
    Insert blanks between all characters of a string

    'hello world' --> 'h e l l o w o r l d'

    Arguments:
    s - the string to be converted

    Returns a string with one blank between each character
    """
    blankremoved = "".join(s.split())
    return " ".join(blankremoved)

def computeCharacterErrorRate(resultlist):
    """
    Computes the Character Error Rate (CER) for a given list of results.

    White spaces are deleted before computation of the edit distance.

    Arguments:
    resultlist - a list of result dictionaries containing the keys reference 
        and hypothesis

    Return the CER
    """
    charresultlist = []
    for result in resultlist:
        reference = insertblanks(result['reference'])
        hypothesis = insertblanks(result['hypothesis'])
        charresultlist.append({'reference': reference, 'hypothesis': hypothesis})
    cer = align.totalTokenErrorRate(charresultlist)
    return cer

    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Result viewer interface")
    parser.add_argument('db', help="SQLAlchemy conform database uri string")
    parser.add_argument('-id', help="Cross-validation id for detail view")
    args = parser.parse_args()
    
    airdb = db.AirDb(args.db)
    resulthandler = ResultHandler(airdb.session)
    if args.id:
        overview = resulthandler.get_cv_detail(args.id)
    else:
        overview = resulthandler.get_cv_overview()
    fieldwidth = [len(str(s))+2 for s in overview[0].values()]
    rowfmt = " ".join("%"+str(w)+"s" for w in fieldwidth)
    #print(rowfmt % tuple(overview[0]))
    for l in overview:
        print((rowfmt % tuple(l.values()))) 
        
