from django.db import models
from jsonfield import JSONField
from fernet_fields import EncryptedCharField

#########################################################
################## LISTS DEFENITIONS ####################
#########################################################
BACKENDS=(
    ('jenkins','Jenkins'),
    ('jira','Jira'),
    ('github','GitHub'),
)

TICKETSTATES=(
    ('open','Open'),
    ('progress','In Work'),
    ('closed','Done'),
)

BUILDSTATES=(
    ('progress','In Work'),
    ('pending','Waiting for Approval'),
    ('success','Successful'),
    ('aborted','Aborted'),
    ('failure','Failed'),
)

BUILDNODETYPE=(
    ('input','User Approval'),
    ('build','Build'),
    ('unit','Unit Tests'),
    ('analysis','Code Analysis'),
    ('security','Security Tests'),
    ('deployment','Deployment'),
    ('packaging','Packaging'),
)

PIPETYPE=(
    ('singlepipeline','Single pipeline'),
    ('multipipeline','Multiple pipeline')
)

AUTH=(
    ('BasicAuth','BasicAuth'),
    ('BasicAuthProxy','BasicAuthProxy')
)

STREAM = (
    ('upstream','upstream'),
    ('downstream','downstream')
)

##########################################################
### ============= MODELS DEFENITIONS ==================###
##########################################################

#################################################
class NoProxy(models.Model):
    ip   = models.GenericIPAddressField(protocol='IPv4',null=True,help_text='IP number to add to Noproxy list')
    name = models.CharField(max_length=200,null=True,help_text='Hostname to add to hosts file')

    def __str__(self):
        return self.name

#################################################
class Remote(models.Model):
    name       = models.CharField(max_length=200,  help_text="Human-Readable name of the instance")
    url        = models.URLField(max_length=200,   help_text="Connection URL ",                            default=None)
    type       = models.CharField(null=True,       max_length=64,                                          choices=BACKENDS)
    project    = models.CharField(max_length=255,  help_text="Name of the project",                        default="NA")
    multipipe  = models.CharField(max_length=255,  help_text="Multipipeline patern", null=True)
    pipetype   = models.CharField(max_length=64,choices=PIPETYPE,default=PIPETYPE[0][0])
    username   = models.CharField(max_length=100,  help_text="Username to use in connection", null=True)
    # fernet_fields does not support Python 3.6
    #password = EncryptedCharField(max_length=100,null=True)
    password = models.CharField(max_length=100, null=True)
    enabled    = models.BooleanField(default=False,help_text="Collector state")
    rproxyuser = models.CharField(max_length=100,  help_text="Reverse proxy username to use in connection",default=None,null=True)
    rproxypass = models.CharField(max_length=100,  help_text="Reverse proxy password to use in connection",default=None,null=True)
    proxy      = models.URLField(null=True,        max_length=200,   help_text="Connection URL ",          default='')
    auth       = models.CharField(null=True,       max_length=64,                                          choices=AUTH)
    apibase    = models.CharField(null=True,       help_text="REST API base URL token", max_length=100,    default=None)
    last_run   = models.DateTimeField(null=True,   help_text="Last time collector was run",                auto_now_add=False)
    next_run   = models.BigIntegerField(null=True, help_text="Next time collector run")
    errors     = models.TextField(null=True,       help_text="Errors happend during last collector failed run")
    pattern    = models.CharField(null=True,       max_length=100, help_text="Search patern for Jenkins collector")
    isprod     = models.BooleanField(default=False, help_text='Deploys to production')

    def __str__(self):
        return self.name

##################################################
##### ========== Models for JIRA ============== ###
##################################################
#
##################################################
class JiraRemote(models.Model):

    name      = models.CharField(max_length=100, help_text="Project name in the ticket system")
    collector = models.ForeignKey(Remote)

    def __str__(self):
        return self.name

#################################################
class JiraIssue(models.Model):

    aggregate         = models.ForeignKey('JiraAggregate', on_delete=models.CASCADE)
    assigne           = models.ForeignKey('JiraPerson',    on_delete=models.CASCADE,related_name="person_assigne")
    components        = models.ForeignKey('JiraComponents',on_delete=models.CASCADE)
    creator           = models.ForeignKey('JiraPerson',    on_delete=models.CASCADE,related_name="person_creator")
    epic              = models.ForeignKey('JiraEpic',      on_delete=models.CASCADE,null=True)
    parent            = models.ForeignKey('JiraParent',    on_delete=models.CASCADE)
    project           = models.ForeignKey('JiraProject',   on_delete=models.CASCADE)
    remote            = models.ForeignKey('JiraRemote',    on_delete=models.CASCADE,null=True)
    sprint            = models.ForeignKey('JiraSprint',    on_delete=models.CASCADE,null=True)
    status            = models.ForeignKey('JiraStatus',    on_delete=models.CASCADE)

    issue_id          = models.CharField(max_length=150,   help_text='Issue Jira id')
    issue_key         = models.CharField(max_length=150,   help_text='Issue Jira key')
    issue_description = models.TextField(                  help_text="Issue description", null=True)
    issue_priority    = models.CharField(max_length=150,   help_text='Issue priority',    null=True)
    issue_progress    = models.IntegerField(               help_text='Issue progress')
    issue_subtsks     = models.CharField(max_length=150,   help_text='Issue subtasks',    null=True)
    issue_summary     = models.TextField(                  help_text="Issue description", null=True)
    issue_types       = models.CharField(max_length=150,   help_text='Issue type')
    issue_url         = models.URLField( max_length=200,   help_text="Issue URL " )
    issue_created     = models.DateTimeField(null=True,    help_text="Issue create date")
    issue_resdate     = models.DateTimeField(null=True,    help_text="Issue resolution")

    def __str__(self):
        return self.issue_key

#######################################################
class JiraAggregate(models.Model):
    progress             = models.IntegerField(help_text="Issue progress",default=0)
    timeestimate         = models.BigIntegerField(help_text="Estimated time to complete",null=True)
    timeoriginalestimate = models.BigIntegerField(help_text="Original time estoimation", null=True)
    timespent            = models.BigIntegerField(help_text="Time spent",                null=True)

#######################################################
class JiraComponents(models.Model):
    name        = models.CharField(max_length=200, help_text="Component name",    null=True, )
    description = models.TextField(                help_text="Error description", null=True, )

    def __str__(self):
        return self.name

#######################################################
class JiraEpic(models.Model):
    name = models.CharField(max_length=200,help_text='Epic name',editable=False,null=True)

    def __str__(self):
        return self.name

#######################################################
class JiraParent(models.Model):
    pa_key = models.CharField(max_length=200,help_text='Parent key string',editable=False,null=True)
    pa_url = models.URLField( max_length=200,help_text="Connection URL ",  editable=False,null=True)

    def __str__(self):
        return self.key

#######################################################
class JiraPerson(models.Model):
    pe_dname = models.CharField(max_length=200, help_text='Person Display Name',editable=False,null=True)
    pe_email = models.EmailField(max_length=254,help_text='Person email',       editable=False,null=True)
    pe_rname = models.CharField(max_length=200, help_text='Person real name',   editable=False,null=True)

    def __str__(self):
        return self.dname

#######################################################
class JiraProject(models.Model):
    pr_key   = models.CharField(max_length=200,help_text='Project key string',editable=False)
    pr_name  = models.CharField(max_length=200,help_text='Project name sting',editable=False)
    pr_url   = models.URLField(max_length=200, help_text="Connection URL",    editable=False)

    def __str__(self):
        return self.name

#######################################################
class JiraSprint(models.Model):
    state        = models.CharField(max_length=100,help_text='SPRINT status'       ,null=True)
    name         = models.CharField(max_length=200,help_text='SPRINT name'         ,null=True)
    startDate    = models.DateTimeField(null=True, help_text="SPRINT start time"   ,auto_now_add=False)
    endDate      = models.DateTimeField(null=True, help_text="SPRINT end time"     ,auto_now_add=False)
    completeDate = models.DateTimeField(null=True, help_text="SPRINT complete time",auto_now_add=False)

    def __str__(self):
        return self.name

#######################################################
class JiraStatus(models.Model):
    name        = models.CharField(max_length=200, help_text="Component name",    blank=True, editable=False)
    description = models.TextField(null=True,      help_text="Error description", blank=True, editable=False)

    def __str__(self):
        return self.name

##########################################################
### ============= Models for Jenkins ================= ###
##########################################################

#################################################
class BuildJob(models.Model):
    name      = models.CharField(max_length=100, help_text="Job name in the builder")
    collector = models.ForeignKey(Remote)

    class Meta:
        unique_together = ('name', 'collector')

    def __str__(self):
        return self.name

#################################################
class Instances(models.Model):
    job    = models.ForeignKey(BuildJob)
    name   = models.CharField(max_length=100, help_text="Instance name")
    status = models.CharField(max_length=250, help_text="Instance status")

    def __str__(self):
        return self.name

#################################################
# Individual Builds from Jenkins
class Multi(models.Model):
    name        = models.CharField(max_length=255,help_text="Multi pipeline name")
    childs_list = JSONField()

#################################################
# Individual Builds from Jenkins
class Build(models.Model):

    bld_id      = models.CharField(null=True,max_length=100, help_text="This field used in orig POC")
    name        = models.CharField(max_length=100, help_text="Name of the build",null=True)
    fullname    = models.CharField(max_length=255, help_text="Full name include branch info", null=True)
    started     = models.DateTimeField(null=True,help_text="Timestamp when this build was run")
    duration    = models.BigIntegerField(help_text="This field used in orig POC",default=0)
    estimate    = models.BigIntegerField(help_text="This field used in orig POC",default=0)
    progress    = models.FloatField(null=True, blank=True, help_text="Progress level from")
    result      = models.CharField(null=True, max_length=64, choices=BUILDSTATES)
    cause       = models.CharField(null=True,max_length=250, help_text="This field used in orig POC")
    coverage    = models.CharField(null=True,max_length=100, help_text="This field used in orig POC")
    deployed    = models.DateTimeField(null=True, blank=True, help_text="Build finished time")
    job         = models.ForeignKey(BuildJob)
    comments    = models.TextField(null=True)
    parent_pipe = models.CharField(null=True,max_length=255,help_text="Name of parent multi pipeline")
    ptype       = models.CharField(null=True, max_length=255, help_text="type of pipeline")
    deppipe     = models.CharField(null=True, max_length=255, help_text="Name of dependent pipeline")
    depinst     = models.CharField(null=True, max_length=255, help_text="Instance of dependent pipeline")
    depdirect   = models.CharField(null=True, max_length=100, choices=STREAM, default=None, help_text='downstream - means this pipeline was startes after initiator run : upstream - means this pipeline triggered recepter run')
    deplocation = models.CharField(null=True, max_length=255, help_text="Instance location of dependent pipeline in parent pipeline")

    class Meta:
        unique_together = ('name', 'job')

    def __str__(self):
        return str(self.job) + " " + self.name

#################################################
# Probably specific to jenkins
class BuildStage(models.Model):

    stg_id   = models.CharField(blank=True,null=True,max_length=100, help_text="This field used to be in sync with POC stucture")
    build    = models.CharField(blank=True,null=True,max_length=100, help_text="This field used to be in sync with POC stucture")
    name     = models.CharField(blank=True,null=True,max_length=100, help_text="Stage name")
    result   = models.CharField(null=True, max_length=64, choices=BUILDSTATES)
    started  = models.DateTimeField(blank=True,null=True,help_text="Timestamp when this stage was entered")
    duration = models.FloatField(null=True, blank=True, help_text="Duration in seconds")
    buildid = models.ForeignKey(Build,null=True)

    #class Meta:
    #    unique_together = ('name', 'buildid')

    def __str__(self):
        return str(self.build) + " " + self.name

#################################################
# Probably specific to jenkins
class BuildNode(models.Model):

    nd_id    = models.CharField(blank=True,null=True,max_length=100, help_text="This field used to be in sync with POC stucture")
    build    = models.CharField(blank=True,null=True,max_length=100, help_text="This field used to be in sync with POC stucture")
    #name     = models.CharField(blank=True,null=True,max_length=100, help_text="Node name")
    stage    = models.CharField(blank=True,null=True,max_length=100, help_text="This field used to be in sync with POC stucture")
    started  = models.DateTimeField(help_text="Timestamp when the node started executing")
    duration = models.FloatField(null=True, blank=True, help_text="Duration in seconds")
    progress = models.CharField(blank=True,null=True,max_length=100, help_text="This field used to be in sync with POC stucture")
    result   = models.CharField(null=True, max_length=64, choices=BUILDSTATES)
    descrpt  = models.CharField(blank=True,null=True,max_length=250, help_text="This field used to be in sync with POC stucture")
    type     = models.CharField(blank=True,null=True,max_length=100, choices=BUILDNODETYPE, help_text="Something like 'unittest' or 'build' or 'input'")
    stageid = models.ForeignKey(BuildStage,null=True)

    def __str__(self):
        return str(self.nd_id)

#################################################
# Pending commands
class RemoteCmd(models.Model):
    rcmd     = JSONField()
    build_id = models.CharField(blank=True, null=True, max_length=100, help_text="Build id relevent to this command")
    remote_id = models.ForeignKey(Remote, null=True)

    def __str__(self):
        return str(self.build_id)

###################################################
# Pojects data
class Projects(models.Model):
    data = JSONField()

    def __str__(self):
        return str(self.id)
