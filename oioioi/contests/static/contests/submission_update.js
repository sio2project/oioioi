$(function() {
  var contest_submissions = {};
  $(window).on('updateStatus', function(event, data) {
    if (data.contest_submissions) {
      if (data.contest_submissions.length != contest_submissions.length || 
          data.contest_submissions.some((el, i) => el.status != contest_submissions[i].status))
        location.reload();
          
      contest_submissions = data.contest_submissions;
    }
  });

  $(window).one('initialStatus', function(ev, data) {
    if (data.contest_submissions)
      contest_submissions = data.contest_submissions;
  });
});
