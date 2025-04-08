from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Property, PropertyImage, CustomUser, Feedback, AgentApplication, AgentRating

class NormalUserSignUpForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'phone_number', 'address')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'normal'
        if commit:
            user.save()
        return user
    
class AgentApplicationForm(forms.ModelForm):
    class Meta:
        model = AgentApplication
        fields = ['license_number', 'experience_years']

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['feedback_text']
        widgets = {
            'feedback_text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter your feedback here'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['phone_number', 'address', 'profile_picture']

class AdminCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'admin'
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['title', 'description', 'price', 'city', 'street', 'zip_code', 'property_type', 'bedrooms', 'bathrooms', 'square_footage', 'year_built']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Provide a detailed description'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Cozy Downtown Apartment'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 250000', 'step': '0.01'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., New York, NY'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 123 Main St'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 10001'}),
            'property_type': forms.Select(attrs={'class': 'form-select'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2', 'min': '0'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1', 'min': '0'}),
            'square_footage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1200', 'min': '0'}),
            'year_built': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2010', 'min': '1800', 'max': '2100'}),
        }

class AgentRatingForm(forms.ModelForm):
    class Meta:
        model = AgentRating
        fields = ['rating', 'review']
        widgets = {'rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)])}

class AgentApplicationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['license_number', 'experience_years', 'phone_number', 'address']
        widgets = {
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., ABC123'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 5', 'min': '0'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 123-456-7890'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 123 Main St, New York, NY'}),
        }

class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = PropertyImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

class PropertyFilterForm(forms.Form):
    PROPERTY_TYPE_CHOICES = [
        ('', 'All Types'),
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('commercial', 'Commercial'),
    ]
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('sold', 'Sold'),
    ]
    min_price = forms.DecimalField(
        label='Min Price', required=False, min_value=0, 
        widget=forms.NumberInput(attrs={'placeholder': 'Min Price', 'step': '0.01'})
    )
    max_price = forms.DecimalField(
        label='Max Price', required=False, min_value=0, 
        widget=forms.NumberInput(attrs={'placeholder': 'Max Price', 'step': '0.01'})
    )
    property_type = forms.ChoiceField(
        choices=PROPERTY_TYPE_CHOICES, required=False, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    location = forms.CharField(
        label='Location', required=False, 
        widget=forms.TextInput(attrs={'placeholder': 'Enter location'})
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, required=False, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )