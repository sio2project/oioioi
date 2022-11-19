from django import forms


class QuizForm(forms.Form):
    def __init__(self, *args, **kwargs):
        if kwargs.has_key('instance'):
            self.quiz = kwargs.pop('instance')
        super(QuizForm, self).__init__(*args, **kwargs)

        if hasattr(self, 'quiz'):
            for i, q in enumerate(self.quiz.user_answers.order_by('id')):
                self.fields["question {}".format(i)] = forms.ModelChoiceField(
                    label="{}. {}".format(i + 1, q.question),
                    queryset=q.question.answers.order_by('?'),
                    widget=forms.RadioSelect,
                    empty_label=None)
