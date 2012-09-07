from django.conf import settings

TEMPLATE = '''
<script type="text/javascript">

  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', '%(tracking_id)s']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();

</script>
'''

def analytics_processor(request):
    tracking_id = getattr(settings, 'GOOGLE_ANALYTICS_TRACKING_ID', None)
    if tracking_id:
        return {'extra_head_analytics': TEMPLATE % {'tracking_id':
            tracking_id}}
    return {}
