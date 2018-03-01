import copy
import uuid
import collections

from ..exceptions import *
from . import parsers


#def read_options(options):
def load_qcdb_defaults(options):

    options.add('qcdb', RottenOption(  # true global
            keyword='memory',
            default='700 mb',
            validator=parsers.parse_memory,
            glossary='Total memory allocation in bytes.'))

    options.add('qcdb', RottenOption(  # true global
            keyword='basis',
            default='',
            validator=lambda x: x.upper(),
            glossary='Primary orbital basis set.'))

    #options.add('qcdb', RottenOption(
    #        keyword='e_convergence',
    #        default=1.e-6,
    #        validator=parsers.parse_convergence,
    #        glossary='Convergence criterion for energy.'))

    options.add('qcdb', RottenOption(  # derived shorthand global
            keyword='scf__e_convergence',
            default=1.e-6,
            validator=parsers.parse_convergence,
            glossary='Convergence criterion for SCF energy.'))

    options.add('qcdb', RottenOption(  # derived shorthand global
            keyword='scf__d_convergence',
            default=1.e-6,
            validator=parsers.parse_convergence,
            glossary='Convergence criterion for SCF density (psi: which is defined as the RMS value of the orbital gradient.'))

    options.add('qcdb', RottenOption(  # true global
            keyword='puream',
            default=True,
            validator=parsers.sphcart,
            glossary="""Do use pure angular momentum basis functions?
  If not explicitly set, the default comes from the basis set.
  **Cfour Interface:** Keyword translates into |cfour__cfour_spherical|."""))

    options.add('qcdb', RottenOption(
            keyword='reference',  # TODO don't want higher and local
            default='',
            validator=lambda x: x.upper(),  # TODO
            glossary="""Reference wavefunction type.
    **Cfour Interface:** Keyword translates into |cfour__cfour_reference|."""))
    #options.add_str("REFERENCE", "RHF", "RHF ROHF UHF CUHF RKS UKS")

    options.add('qcdb', RottenOption(
            keyword='scf__reference',
            default='',
            validator=lambda x: x.upper(),  # TODO
            glossary="""Reference wavefunction type.
    **Cfour Interface:** Keyword translates into |cfour__cfour_reference|."""))
    #options.add_str("REFERENCE", "RHF", "RHF ROHF UHF CUHF RKS UKS")

    options.add('qcdb', RottenOption(
            keyword='scf_type',  # TODO ditto, 2-leveled
            default='',
            validator=lambda x: x.upper(),  # TODO
            glossary="""What algorithm to use for the SCF computation. See Table :ref:`SCF
    Convergence & Algorithm <table:conv_scf>` for default algorithm for
    different calculation types."""))
    #options.add_str("SCF_TYPE", "PK", "DIRECT DF PK OUT_OF_CORE CD GTFOCK");

    options.add('qcdb', RottenOption(
            keyword='scf__scf_type',
            default='',
            validator=lambda x: x.upper(),  # TODO
            glossary="""What algorithm to use for the SCF computation. See Table :ref:`SCF
    Convergence & Algorithm <table:conv_scf>` for default algorithm for
    different calculation types."""))
    #options.add_str("SCF_TYPE", "PK", "DIRECT DF PK OUT_OF_CORE CD GTFOCK");

    options.add('qcdb', RottenOption(
            keyword='scf__maxiter',
            default=100,
            validator=parsers.positive_integer,
            glossary="""Maximum number of iterations.
    **Cfour Interface:** Keyword translates into |cfour__cfour_scf_maxcyc|."""))

    options.add('qcdb', RottenOption(
            keyword='scf__damping_percentage',
            default=0.0,
            validator=parsers.percentage,
            glossary="""The amount (percentage) of damping to apply to the early density updates.
        0 will result in a full update, 100 will completely stall the update. A
        value around 20 (which corresponds to 20\% of the previous iteration's
        density being mixed into the current density)
        could help to solve problems with oscillatory convergence."""))

#    options.add('qcdb', RottenOption(
#            keyword='',
#            default=,
#            validator=,
#            glossary="""."""))



class RottenOptions(object):
    mark_of_the_user = '00000000'
    mark_of_the_default = 'ffffffff'

    def __init__(self):
        self.scroll = collections.defaultdict(dict)

    def __str__(self):
        text = []
        for pkg in self.scroll:
            text.append('  <<<  {}  >>>'.format(pkg))
            for opt, oopt in sorted(self.scroll[pkg].items()):
                text.append(str(oopt))

        return '\n'.join(text)

    def add(self, package, opt):
        up = package.upper()
        if up in ['QCDB', 'PSI4', 'CFOUR', 'DFTD3']:
            self.scroll[up][opt.keyword] = opt
        else:
            raise ValidationError('Domain not supported: {}'.format(package))
    
    def require(self, package, option, value, accession, verbose=1):
        self._set(True, package, option, value, accession, verbose)

    def suggest(self, package, option, value, accession, verbose=1):
        self._set(False, package, option, value, accession, verbose)

    def _set(self, imperative, package, option, value, accession, verbose):
        count = 0
        for ropt, oropt in self.scroll[package.upper()].items():
            if ropt.endswith(option.upper()):
                overlap = len(option)
                if imperative:
                    oropt.require(value, overlap=overlap, accession=accession, verbose=verbose)
                else:
                    oropt.suggest(value, overlap=overlap, accession=accession, verbose=verbose)
                count += 1
        if count == 0:
            raise ValidationError('Option ({}) does not exist in domain ({}).'.format(option, package))

    def unwind_by_accession(self, accession):
        for pkg in self.scroll:
            for ropt, oropt in self.scroll[pkg].items():
               oropt.history = [entry for entry in oropt.history if entry[3] != accession]
            

class RottenOption(object):
    mark_of_the_user = '00000000'
    mark_of_the_default = 'ffffffff'

    def __init__(self, keyword, default, validator, glossary='', expert=False):
        self.keyword = keyword.upper()
        self.glossary = glossary
        self.validator = validator
        self.history = []  # list of quads (value, required, overlap, accession)
        self.suggest(default, accession=self.mark_of_the_default, verbose=0)
        #self.default = copy.deepcopy(self.value)
        self.has_changed = False
        self.expert = expert

    def __str__(self):
        text = []
        text.append('  {:23} {:>30} {} {}'.format(
                                        self.keyword + ':',
                                        str(self.value),
                                        '  ' if self.is_default() else '<>',
                                        #'(' + str(self.default) + ')')
                                        '(' + str(self.history[0][0]) + ')'))
        #text.extend([str(entry) for entry in self.history])
        return '\n'.join(text)

    @property
    def value(self):
        """The all-important `self.value` is read-only and computed on-the-fly from `self.history`."""

        scores = [cand[2] + 100 * int(cand[1]) for cand in self.history]
        max_score = max(scores)

        # only catch user and driver reqd of highest relevance and most recent vintage
        user = None
        for score, candidate in zip(reversed(scores), reversed(self.history)):
            if score == max_score and candidate[3] == self.mark_of_the_user:
                user = candidate
                break

        driver = None
        for score, candidate in zip(reversed(scores), reversed(self.history)):
            if score == max_score and candidate[3] != self.mark_of_the_user:
                driver = candidate
                break

        if user is None and driver is None:
            raise OptionReconciliationError('No info')
        elif user is None and driver is not None:
            val = driver[0]
        elif user is not None and driver is None:
            val = user[0]
        elif user is not None and driver is not None:
            if user[0] == driver[0]:
                val = user[0]
            else:
                raise OptionReconciliationError(
                    'Conflicting option requirements btwn user ({}) and driver ({})'.
                    format(user[0], driver[0]))
        
        return val
        
    
    #@value.setter
    #def value(self, val):
    #    self._value = self._check(val)
    #    self.has_changed = True

    def suggest(self, value, overlap=None, accession=None, verbose=1):
        self._set(False, value, overlap, accession, verbose)
        
    def require(self, value, overlap=None, accession=None, verbose=1):
        """

        Parameters
        ----------
        value
            Asserted value for option `self`. Will be checked against
            `self.validator` before function returns. May still be incompatible with
            other `require` calls of same priority, but that won't be checked until
            `self.value` is accessed.
        overlap : int, optional
            Specificity of assertion. If `self.keyword='CC_MAXITER'` and `value`
            is set for `MAXITER`, `overlap=7`, whereas if set for `CC_MAXITER`,
            `overlap=10`.
        accession
            Tag of who is setting this option.

        """
        self._set(True, value, overlap, accession, verbose)

    def _set(self, imperative, value, overlap, accession, verbose=1):
        if overlap is None:
            overlap = len(self.keyword)
        if accession is None:
            accession = uuid.uuid4()

        self.history.append((self._check(value), imperative, overlap, accession))

        if verbose >= 1:
            added = self.history[-1]
            print('Setting {} to {} priority {} accession {}'.
                format(self.keyword, added[0], added[2] + 100 * int(added[1]), added[3]))

    def _check(self, val):
        """Common function to check `val` against `self.validator` for setting, defaulting, etc."""

        try:
            nuval = self.validator(val)
        except Exception as err:
            raise OptionValidationError(
                'Option ({}) value ({}) does not pass.'.format(self.keyword, val)) from err
        return nuval

    def is_default(self):
        #return self.value == self.default
        return self.value == self.history[0][0]
