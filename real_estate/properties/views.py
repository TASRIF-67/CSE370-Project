# properties/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from .forms import NormalUserSignUpForm, AgentRatingForm, PropertyForm, AdminCreationForm, AgentApplicationForm, FeedbackForm, PropertyFilterForm, UserProfileForm, AgentRating 
from .models import Property, PropertyImage, Interest, Transaction, CustomUser, Feedback, AgentApplication
from django.forms import modelformset_factory
from .forms import PropertyForm, PropertyImageForm
from django.core.paginator import Paginator

def about_us(request):
    return render(request, 'about_us.html')

#=========HOME PAGE============
def home(request):
    # SELECT * FROM properties_property WHERE status = 'approved';
    properties = Property.objects.filter(status='approved')

    interested_property_ids = set()
    
    if request.user.is_authenticated:
        # SELECT * FROM properties_property WHERE status = 'approved' AND seller_id != <request.user.id>;
        # properties = properties.exclude(seller=request.user)
        # SELECT property_id FROM properties_interest WHERE user_id = <request.user.id>;
        interested_property_ids = set(request.user.interests.values_list('property_id', flat=True))

    # Search and filter logic
    query = request.GET.get('q', '')
    property_type = request.GET.get('property_type', '')
    city = request.GET.get('city', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    bedrooms = request.GET.get('bedrooms', '')

    if query:
        # SELECT * FROM properties_property WHERE status = 'approved' AND (title LIKE '%<query>%' OR description LIKE '%<query>%');
        properties = properties.filter(
            models.Q(title__icontains=query) |
            models.Q(description__icontains=query)
        )
    if property_type:
        # SELECT * FROM properties_property WHERE status = 'approved' AND property_type = '<property_type>';
        properties = properties.filter(property_type=property_type)
    if city:
        # SELECT * FROM properties_property WHERE status = 'approved' AND city LIKE '%<city>%';
        properties = properties.filter(city__icontains=city)
    if min_price:
        # SELECT * FROM properties_property WHERE status = 'approved' AND price >= <min_price>;
        properties = properties.filter(price__gte=min_price)
    if max_price:
        # SELECT * FROM properties_property WHERE status = 'approved' AND price <= <max_price>;
        properties = properties.filter(price__lte=max_price)
    if bedrooms:
        # SELECT * FROM properties_property WHERE status = 'approved' AND bedrooms >= <bedrooms>;
        properties = properties.filter(bedrooms__gte=bedrooms)

    return render(request, 'home.html', {
        'properties': properties,
        'interested_property_ids': interested_property_ids
    })


#=========NORMAL SIGNUP============
def normal_signup(request):
    if request.method == 'POST':
        form = NormalUserSignUpForm(request.POST)
        if form.is_valid():
            # INSERT INTO properties_customuser (username, password, email, phone... ) 
            # VALUES (<form.cleaned_data['username']>, <hashed_password>, <form.cleaned_data['email']>, ...);
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome aboard.")
            return redirect('dashboard')
        else:
            errors = form.errors.get_json_data()
            error_msg = "Registration failed. Please correct the following:\n"
            error_msg += "\n".join([f"{field}: {err[0]['message']}" for field, err in errors.items()])
            messages.error(request, error_msg)
    else:
        form = NormalUserSignUpForm()
    return render(request, 'signup.html', {'form': form, 'role': 'Normal User'})

#=========CUSTOM LOGIN VIEW============
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Login successful!")
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        errors = form.errors.get_json_data()
        error_msg = "Login failed. Please check your credentials."
        if errors:
            error_msg += "\nErrors:\n" + "\n".join([f"{field}: {err[0]['message']}" for field, err in errors.items()])
        messages.error(self.request, error_msg)
        return response

#=========DASHBOARD============
@login_required
def dashboard(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role == 'normal':
        return user_dashboard(request)
    elif request.user.role == 'agent':
        return agent_dashboard(request)
    elif request.user.role == 'admin':
        return admin_dashboard(request)
    return redirect('home')


#=========USER DASHBOARD============
@login_required
def user_dashboard(request):
    # SELECT * FROM properties_property WHERE seller_id = <request.user.id>;
    properties = Property.objects.filter(seller=request.user)
    # SELECT * FROM properties_transaction WHERE buyer_id = <request.user.id>;
    transactions = Transaction.objects.filter(buyer=request.user)
    # SELECT * FROM properties_interest WHERE user_id = <request.user.id>;
    interests = Interest.objects.filter(interested_user=request.user)
    # SELECT * FROM properties_feedback WHERE user_id = <request.user.id>;
    feedbacks = Feedback.objects.filter(user=request.user) if 'Feedback' in globals() else []
    context = {
        'properties': properties,
        'transactions': transactions,
        'interests': interests,
        'feedbacks': feedbacks,
    }
    return render(request, 'user_dashboard.html', context)

#=========AGENT DASHBOARD============
@login_required
def agent_dashboard(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'agent':
        return redirect('dashboard')
    # SELECT * FROM properties_property WHERE assigned_agent_id = <request.user.id>;
    properties = Property.objects.filter(assigned_agent=request.user)
    # SELECT * FROM properties_transaction WHERE agent_id = <request.user.id>;
    transactions = Transaction.objects.filter(agent=request.user)
    # SELECT * FROM properties_interest WHERE assigned_agent_id = <request.user.id>;
    interests = Interest.objects.filter(assigned_agent=request.user)
    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id')
        # SELECT * FROM properties_transaction WHERE id = <transaction_id> AND agent_id = <request.user.id>;
        transaction = get_object_or_404(Transaction, id=transaction_id, agent=request.user)
        # UPDATE properties_transaction SET payment_status = 'approved' WHERE id = <transaction_id>;
        transaction.payment_status = 'approved'
        transaction.save()
        # UPDATE properties_customuser SET total_listings = total_listings + 1 WHERE id = <request.user.id>;
        request.user.total_listings += 1
        request.user.save()
    context = {
        'properties': properties,
        'transactions': transactions,
        'interests': interests,
    }
    return render(request, 'agent_dashboard.html', context)

#=========ADMIN DASHBOARD============
@login_required
def admin_dashboard(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('dashboard')
    # SELECT * FROM properties_property;
    properties = Property.objects.all()
    # SELECT * FROM properties_property WHERE status = 'pending';
    pending_properties = Property.objects.filter(status='pending')
    # SELECT * FROM properties_customuser WHERE agent_application_status = 'pending';
    agent_requests = CustomUser.objects.filter(agent_application_status='pending')
    # SELECT * FROM properties_transaction;
    transactions = Transaction.objects.all()
    # SELECT * FROM properties_interest WHERE assigned_agent_id IS NULL;
    unassigned_interests = Interest.objects.filter(assigned_agent__isnull=True)  # Notify admin
    # SELECT * FROM properties_customuser WHERE role = 'agent';
    agents = CustomUser.objects.filter(role='agent')
    if request.method == 'POST':
        interest_id = request.POST.get('interest_id')
        agent_id = request.POST.get('agent_id')
        # SELECT * FROM properties_interest WHERE id = <interest_id> AND assigned_agent_id IS NULL;
        interest = get_object_or_404(Interest, id=interest_id, assigned_agent__isnull=True)
        # SELECT * FROM properties_customuser WHERE id = <agent_id> AND role = 'agent';
        agent = get_object_or_404(CustomUser, id=agent_id, role='agent')
        # UPDATE properties_interest SET assigned_agent_id = <agent_id> WHERE id = <interest_id>;
        interest.assigned_agent = agent
        # UPDATE properties_property SET assigned_agent_id = <agent_id> WHERE id = <interest.property.id>;
        interest.property.assigned_agent = agent  # Assign to property too
        interest.save()
        interest.property.save()
    context = {
        'properties': properties,
        'pending_properties': pending_properties,
        'agent_requests': agent_requests,
        'transactions': transactions,
        'unassigned_interests': unassigned_interests,
        'agents': agents,
    }
    return render(request, 'admin_dashboard.html', context)

#=========USER DETAIL============
@login_required
def user_detail(request, user_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can access this page.")
        return redirect('home')
    
    if user_id == request.user.id:
        messages.error(request, "You cannot view your own details here.")
        return redirect('manage_users')
    
    # SELECT * FROM properties_customuser WHERE id = <user_id>;
    viewed_user = get_object_or_404(CustomUser, id=user_id)
    
    context = {
        'viewed_user': viewed_user
    }
    
    # For normal users: properties bought and sold
    if viewed_user.role == 'normal':
        # SELECT * FROM properties_transaction WHERE buyer_id = <viewed_user.id> AND payment_status = 'approved';
        properties_bought = Transaction.objects.filter(buyer=viewed_user, payment_status='approved')
        # SELECT * FROM properties_property WHERE seller_id = <viewed_user.id> AND status = 'sold';
        properties_sold = Property.objects.filter(seller=viewed_user, status='sold')
        context['properties_bought'] = properties_bought
        context['properties_sold'] = properties_sold
    
    # For agents: total workings
    elif viewed_user.role == 'agent':
        # SELECT * FROM properties_transaction WHERE agent_id = <viewed_user.id> AND payment_status = 'approved';
        agent_workings = Transaction.objects.filter(agent=viewed_user, payment_status='approved')
        # SELECT COUNT(*) FROM properties_transaction WHERE agent_id = <viewed_user.id> AND payment_status = 'approved';
        total_workings = agent_workings.count()
        context['agent_workings'] = agent_workings
        context['total_workings'] = total_workings
    
    return render(request, 'user_detail.html', context)

#=========EDIT USER============
@login_required
def edit_user(request, user_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can edit users.")
        return redirect('dashboard')
    # SELECT * FROM properties_customuser WHERE id = <user_id>;
    user = get_object_or_404(CustomUser, id=user_id)
    # SELECT role FROM properties_customuser WHERE id = <user_id>;
    if user.role == 'admin':
        messages.error(request, "Admins cannot edit other admins.")
        return redirect('manage_users')
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        role = request.POST.get('role')  # Allow role change
        if form.is_valid():
            if role in ['normal', 'agent'] and role != user.role:
                user.role = role
                if role == 'normal':
                    user.license_number = None
                    user.experience_years = None
                    user.total_listings = 0
                    user.average_rating = 0.0
            # UPDATE properties_customuser SET role = <role>, license_number = NULL, experience_years = NULL, 
            # total_listings = 0, average_rating = 0.0, <other_form_fields> WHERE id = <user_id>;
            form.save()
            user.save()
            messages.success(request, f"User {user.username} updated successfully.")
            return redirect('manage_users')
    else:
        form = UserProfileForm(instance=user)
    return render(request, 'edit_user.html', {'form': form, 'user': user})

#=========DELETE USER============
@login_required
def delete_user(request, user_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can delete users.")
        return redirect('dashboard')
    # SELECT * FROM properties_customuser WHERE id = <user_id>;
    user = get_object_or_404(CustomUser, id=user_id)
    # SELECT role FROM properties_customuser WHERE id = <user_id>;
    if user.role == 'admin':
        messages.error(request, "Admins cannot delete other admins.")
        return redirect('manage_users')
    if request.method == 'POST':
        # DELETE FROM properties_customuser WHERE id = <user_id>;
        user.delete()
        messages.success(request, f"User {user.username} deleted successfully.")
        return redirect('manage_users')
    return render(request, 'delete_user.html', {'user': user})



#=========CREATE PROPERTY============
@login_required
def create_property(request):
    ImageFormSet = modelformset_factory(PropertyImage, form=PropertyImageForm, extra=3)  # 3 extra image fields
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        formset = ImageFormSet(request.POST, request.FILES, queryset=PropertyImage.objects.none())
        if form.is_valid() and formset.is_valid():
            property = form.save(commit=False)
            property.seller = request.user
            property.status = 'pending'
            # INSERT INTO properties_property (seller_id, status, title, description, price, city, bedrooms, property_type, ...)
            # VALUES (<request.user.id>, 'pending', <form.cleaned_data['title']>, <form.cleaned_data['description']>, ...);
            property.save()
            for image_form in formset:
                if image_form.cleaned_data.get('image'):  # Only save if an image is provided
                    # INSERT INTO properties_propertyimage (property_id, image) 
                    # VALUES (<property.id>, <image_form.cleaned_data['image']>);
                    PropertyImage.objects.create(property=property, image=image_form.cleaned_data['image'])
            messages.success(request, "Property listed successfully. Awaiting admin approval.")
            return redirect('dashboard')
    else:
        form = PropertyForm()
        formset = ImageFormSet(queryset=PropertyImage.objects.none())
    return render(request, 'create_property.html', {'form': form, 'formset': formset})

#=========EDIT PROPERTY============
@login_required
def edit_property(request, property_id):
    # SELECT * FROM properties_property WHERE id = <property_id> AND seller_id = <request.user.id>;
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=property)
        images = request.FILES.getlist('images')
        if form.is_valid():
            property = form.save(commit=False)
            property.status = 'under_review'
            # UPDATE properties_property SET status = 'under_review', title = <form.cleaned_data['title']>, 
            # description = <form.cleaned_data['description']>, price = <form.cleaned_data['price']>, ... 
            # WHERE id = <property_id>;
            property.save()
            for image in images:
                # INSERT INTO properties_propertyimage (property_id, image) 
                # VALUES (<property.id>, <image>);
                PropertyImage.objects.create(property=property, image=image)
            messages.success(request, "Property updated and under review.")
            return redirect('dashboard')
    else:
        form = PropertyForm(instance=property)
    return render(request, 'edit_property.html', {'form': form, 'property': property})

#=========DELETE PROPERTY============
@login_required
def delete_property(request, property_id):
    # SELECT * FROM properties_property WHERE id = <property_id> AND seller_id = <request.user.id>;
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    if request.method == 'POST':
        # DELETE FROM properties_property WHERE id = <property_id>;
        property.delete()
        messages.success(request, "Property deleted.")
        return redirect('dashboard')
    return render(request, 'delete_property.html', {'property': property})

#=========PROPERTY DETAIL============

@login_required
def property_detail(request, property_id):
    property = get_object_or_404(Property, id=property_id)
    
    # Check if the logged-in user already expressed interest
    has_expressed_interest = Interest.objects.filter(
        property=property,
        interested_user=request.user
    ).exists()
    
    return render(request, 'property_detail.html', {
        'property': property,
        'has_expressed_interest': has_expressed_interest,
    })

#=========EXPRESS INTEREST============
@login_required
def express_interest(request, property_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'normal':
        return redirect('home')
    # SELECT * FROM properties_property WHERE id = <property_id> AND status = 'approved';
    property = get_object_or_404(Property, id=property_id, status='approved')
    if request.user == property.seller:
        messages.error(request, "You cannot express interest in your own property.")
        return redirect('home')
    # SELECT EXISTS(SELECT 1 FROM properties_interest WHERE property_id = <property_id> AND user_id = <request.user.id>);
    if not Interest.objects.filter(property=property, interested_user=request.user).exists():
        # INSERT INTO properties_interest (property_id, user_id, assigned_agent_id, status) 
        # VALUES (<property.id>, <request.user.id>, NULL, 'pending');
        Interest.objects.create(
            property=property,
            interested_user=request.user,
            assigned_agent=None,  # No agent assigned here
            status='pending'  # Stays pending until "Contact an Agent"
        )
        messages.success(request, "Interest expressed successfully.")
    return redirect('user_interests')


#=========CONTACT AGENT============
@login_required
def contact_agent(request, interest_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'normal':
        return redirect('home')
    # SELECT * FROM properties_interest WHERE id = <interest_id> AND user_id = <request.user.id>;
    interest = get_object_or_404(Interest, id=interest_id, interested_user=request.user)
    if interest.assigned_agent is None and interest.status != 'assigning':
        interest.status = 'assigning'  # New: Change status to "Assigning…"
        # UPDATE properties_interest SET status = 'assigning' WHERE id = <interest_id>;
        interest.save()
        messages.success(request, "An agent will contact you shortly.")
    return redirect('user_interests')

#=========SUBMIT FEEDBACK============
@login_required
def submit_feedback(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'normal':
        messages.error(request, "Only normal users can submit feedback.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            # INSERT INTO properties_feedback (user_id, <other_form_fields>) 
            # VALUES (<request.user.id>, <form.cleaned_data['field1']>, ...);
            feedback.save()
            messages.success(request, "Feedback submitted.")
            return redirect('dashboard')
    else:
        form = FeedbackForm()
    return render(request, 'feedback.html', {'form': form})

#=========UPDATE PROFILE============
@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            # UPDATE properties_customuser SET <form_fields> WHERE id = <request.user.id>;
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('dashboard')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'update_profile.html', {'form': form})

#=========MANAGE USERS============
@login_required
def manage_users(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can access this page.")
        return redirect('home')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        # SELECT * FROM properties_customuser WHERE id = <user_id>;
        user = get_object_or_404(CustomUser, id=user_id)
        if user != request.user:
            # DELETE FROM properties_customuser WHERE id = <user_id>;
            user.delete()
            messages.success(request, f"User '{user.username}' deleted successfully.")
        else:
            messages.error(request, "You cannot delete yourself.")
        return redirect('manage_users')
    
    # Split users by role
    # SELECT * FROM properties_customuser WHERE role = 'agent';
    agents = CustomUser.objects.filter(role='agent')
    # SELECT * FROM properties_customuser WHERE role = 'normal';
    normal_users = CustomUser.objects.filter(role='normal')
    context = {
        'agents': agents,
        'normal_users': normal_users,
        'current_user': request.user  # To disable delete for self
    }
    return render(request, 'manage_users.html', context)

#=========APPROVE PROPERTY============
@login_required
def approve_property(request, property_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('dashboard')
    # SELECT * FROM properties_property WHERE id = <property_id>;
    property = get_object_or_404(Property, id=property_id)
    property.status = 'approved'
    # UPDATE properties_property SET status = 'approved' WHERE id = <property_id>;
    property.save()
    messages.success(request, f"Property '{property.title}' approved.")
    return redirect('dashboard')

#=========MARK SOLD============
@login_required
def mark_sold(request, property_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('dashboard')
    # SELECT * FROM properties_property WHERE id = <property_id>;
    property = get_object_or_404(Property, id=property_id)
    if request.method == 'POST':
        buyer_id = request.POST['buyer']
        # SELECT * FROM properties_customuser WHERE id = <buyer_id>;
        buyer = get_object_or_404(CustomUser, id=buyer_id)
        # INSERT INTO properties_transaction (property_id, buyer_id, seller_id, amount) 
        # VALUES (<property.id>, <buyer.id>, <property.seller.id>, <property.price>);
        Transaction.objects.create(property=property, buyer=buyer, seller=property.seller, amount=property.price)
        property.status = 'sold'
        # UPDATE properties_property SET status = 'sold' WHERE id = <property_id>;
        property.save()
        messages.success(request, f"Property '{property.title}' marked as sold.")
    return redirect('dashboard')

#=========CREATE ADMIN============
@login_required
def create_admin(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        form = AdminCreationForm(request.POST)
        if form.is_valid():
            # INSERT INTO properties_customuser (username, password, email, role, ...) 
            # VALUES (<form.cleaned_data['username']>, <hashed_password>, <form.cleaned_data['email']>, 'admin', ...);
            form.save()
            messages.success(request, "Admin created.")
            return redirect('manage_users')
    else:
        form = AdminCreationForm()
    return render(request, 'create_admin.html', {'form': form})

#=========REMOVE ADMIN============
@login_required
def remove_admin(request, user_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin' or request.user.id == user_id:
        return redirect('dashboard')
    # SELECT * FROM properties_customuser WHERE id = <user_id> AND role = 'admin';
    user = get_object_or_404(CustomUser, id=user_id, role='admin')
    # DELETE FROM properties_customuser WHERE id = <user_id>;
    user.delete()
    messages.success(request, f"Admin '{user.username}' removed.")
    return redirect('dashboard')

#=========ADMIN EDIT PROPERTY============
@login_required
def admin_edit_property(request, property_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can edit properties.")
        return redirect('dashboard')
    # SELECT * FROM properties_property WHERE id = <property_id>;
    property = get_object_or_404(Property, id=property_id)
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=property)
        images = request.FILES.getlist('images')
        if form.is_valid():
            # UPDATE properties_property SET title = <form.cleaned_data['title']>, 
            # description = <form.cleaned_data['description']>, price = <form.cleaned_data['price']>, ... 
            # WHERE id = <property_id>;
            property = form.save()
            for image in images:
                # INSERT INTO properties_propertyimage (property_id, image) 
                # VALUES (<property.id>, <image>);
                PropertyImage.objects.create(property=property, image=image)
            messages.success(request, f"Property '{property.title}' updated successfully.")
            return redirect('admin_dashboard')  # Updated to use URL name
    else:
        form = PropertyForm(instance=property)
    return render(request, 'admin_edit_property.html', {'form': form, 'property': property})

#=========ADMIN DELETE PROPERTY============
@login_required
def admin_delete_property(request, property_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can delete properties.")
        return redirect('dashboard')
    # SELECT * FROM properties_property WHERE id = <property_id>;
    property = get_object_or_404(Property, id=property_id)
    if request.method == 'POST':
        # DELETE FROM properties_property WHERE id = <property_id>;
        property.delete()
        messages.success(request, f"Property '{property.title}' deleted successfully.")
        return redirect('admin_dashboard')  # Updated to use URL name
    return render(request, 'admin_delete_property.html', {'property': property})

#=========APPLY AGENT============
@login_required
def apply_agent(request):
    # SELECT role, agent_application_status FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'normal' or request.user.agent_application_status != 'none':
        return render(request, 'apply_agent_error.html', {'message': 'You cannot apply as an agent at this time.'})
    
    if request.method == 'POST':
        form = AgentApplicationForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.agent_application_status = 'pending'
            # UPDATE properties_customuser SET agent_application_status = 'pending', <other_form_fields> 
            # WHERE id = <request.user.id>;
            user.save()
            messages.success(request, "The admin will review and approve your request.")
            return redirect('home')
        return render(request, 'apply_agent.html', {'form': form, 'error': 'Please correct the errors below.'})
    
    form = AgentApplicationForm(instance=request.user)
    return render(request, 'apply_agent.html', {'form': form})

#=========APPROVE AGENT============
@login_required
def approve_agent(request, user_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('dashboard')
    # SELECT * FROM properties_customuser WHERE id = <user_id> AND agent_application_status = 'pending';
    user = get_object_or_404(CustomUser, id=user_id, agent_application_status='pending')
    user.role = 'agent'
    user.agent_application_status = 'approved'
    user.total_listings = 0  # Initialize agent stats
    user.average_rating = 0.0
    # UPDATE properties_customuser SET role = 'agent', agent_application_status = 'approved', 
    # total_listings = 0, average_rating = 0.0 WHERE id = <user_id>;
    user.save()
    return redirect('admin_dashboard')

#=========REJECT AGENT============
@login_required
def reject_agent(request, user_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('dashboard')
    # SELECT * FROM properties_customuser WHERE id = <user_id> AND agent_application_status = 'pending';
    user = get_object_or_404(CustomUser, id=user_id, agent_application_status='pending')
    user.agent_application_status = 'rejected'
    # UPDATE properties_customuser SET agent_application_status = 'rejected' WHERE id = <user_id>;
    user.save()
    return redirect('admin_dashboard')

#=========RATE AGENT============
@login_required
def rate_agent(request, agent_id):
    # SELECT * FROM properties_customuser WHERE id = <agent_id> AND role = 'agent';
    agent = get_object_or_404(CustomUser, id=agent_id, role='agent')
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'normal':
        messages.error(request, "Only normal users can rate agents.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = AgentRatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.user = request.user
            rating.agent = agent
            # INSERT INTO properties_agentrating (user_id, agent_id, rating, comment, ...) 
            # VALUES (<request.user.id>, <agent.id>, <form.cleaned_data['rating']>, <form.cleaned_data['comment']>, ...);
            rating.save()
            messages.success(request, "Rating submitted.")
            return redirect('dashboard')
    else:
        form = AgentRatingForm()
    return render(request, 'rate_agent.html', {'form': form, 'agent': agent})

#=========COMPLETED TASKS============
@login_required
def completed_tasks(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'agent':
        messages.error(request, "Only agents can access this page.")
        return redirect('home')
    
    # SELECT t.*, p.* FROM properties_transaction t 
    # JOIN properties_property p ON t.property_id = p.id 
    # WHERE t.agent_id = <request.user.id> AND t.payment_status = 'approved' 
    # ORDER BY t.created_at DESC;
    transactions = Transaction.objects.filter(agent=request.user, payment_status='approved').select_related('property').order_by('-created_at')
    
    return render(request, 'completed_tasks.html', {'transactions': transactions})

#=========CONFIRM TRANSACTION============
@login_required
def confirm_transaction(request, property_id):
    # SELECT * FROM properties_property WHERE id = <property_id> AND assigned_agent_id = <request.user.id>;
    property = get_object_or_404(Property, id=property_id, assigned_agent=request.user)
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'agent':
        messages.error(request, "Only agents can confirm transactions.")
        return redirect('dashboard')
    if request.method == 'POST':
        buyer_id = request.POST['buyer']
        # SELECT * FROM properties_customuser WHERE id = <buyer_id>;
        buyer = get_object_or_404(CustomUser, id=buyer_id)
        commission = property.price * (property.commission_rate / 100)
        # INSERT INTO properties_transaction (property_id, buyer_id, agent_id, amount, commission) 
        # VALUES (<property.id>, <buyer.id>, <request.user.id>, <property.price>, <commission>);
        Transaction.objects.create(
            property=property, buyer=buyer, agent=request.user,
            amount=property.price, commission=commission
        )
        property.status = 'sold'
        # UPDATE properties_property SET status = 'sold' WHERE id = <property_id>;
        property.save()
        # UPDATE properties_customuser SET total_listings = total_listings + 1 WHERE id = <request.user.id>;
        request.user.total_listings += 1
        request.user.save()
        messages.success(request, "Transaction confirmed.")
        return redirect('dashboard')
    return render(request, 'confirm_transaction.html', {'property': property})

#=========USER LISTINGS============
@login_required
def user_listings(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'normal':
        return redirect('dashboard')
    # SELECT * FROM properties_property WHERE seller_id = <request.user.id>;
    properties = Property.objects.filter(seller=request.user)
    return render(request, 'user_listings.html', {'properties': properties})

#=========AGENT INTERESTS============
@login_required
def agent_interests(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'agent':
        messages.error(request, "Only agents can access this page.")
        return redirect('home')
    
    # SELECT t.*, p.* FROM properties_transaction t 
    # JOIN properties_property p ON t.property_id = p.id 
    # WHERE t.agent_id = <request.user.id> AND t.payment_status = 'approved' AND p.status = 'sold' 
    # ORDER BY t.date DESC;
    completed_tasks = Transaction.objects.filter(
        agent=request.user,
        payment_status='approved',
        property__status='sold'
    ).select_related('property').order_by('-date')
    
    return render(request, 'agent_interests.html', {'completed_tasks': completed_tasks})

#=========UPDATE PROPERTY STATUS============
@login_required
def update_property_status(request, property_id):
    # SELECT * FROM properties_property WHERE id = <property_id>;
    property = get_object_or_404(Property, id=property_id)
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role not in ['agent', 'admin'] or (request.user.role == 'agent' and property.assigned_agent != request.user):
        return render(request, 'error.html', {'message': 'You are not authorized to update this property.'})
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['pending', 'approved', 'sold']:
            property.status = status
            # UPDATE properties_property SET status = <status> WHERE id = <property_id>;
            property.save()
            if status == 'sold' and request.user.role == 'agent':
                # SELECT i.* FROM properties_interest i WHERE i.property_id = <property.id> LIMIT 1;
                # INSERT INTO properties_transaction (buyer_id, property_id, agent_id, amount) 
                # VALUES (<interest.interested_user.id>, <property.id>, <request.user.id>, <property.price>);
                Transaction.objects.create(
                    buyer=Interest.objects.filter(property=property).first().interested_user,
                    property=property,
                    agent=request.user,
                    amount=property.price
                )
            return redirect('dashboard')
    return render(request, 'update_property_status.html', {'property': property})

#=========USER PROPERTIES============
@login_required
def user_properties(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'normal':
        return redirect('home')
    # SELECT * FROM properties_property WHERE seller_id = <request.user.id>;
    properties = Property.objects.filter(seller=request.user)
    return render(request, 'user_properties.html', {'properties': properties})

#=========USER TRANSACTIONS============
@login_required
def user_transactions(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'normal':
        return redirect('home')
    
    # Fetch transactions where the user is the buyer or seller
    # SELECT t.* FROM properties_transaction t 
    # JOIN properties_property p ON t.property_id = p.id 
    # JOIN properties_customuser b ON t.buyer_id = b.id 
    # JOIN properties_customuser a ON t.agent_id = a.id 
    # WHERE t.buyer_id = <request.user.id>
    # UNION
    # SELECT t.* FROM properties_transaction t 
    # JOIN properties_property p ON t.property_id = p.id 
    # JOIN properties_customuser s ON p.seller_id = s.id 
    # JOIN properties_customuser b ON t.buyer_id = b.id 
    # JOIN properties_customuser a ON t.agent_id = a.id 
    # WHERE p.seller_id = <request.user.id>;
    transactions = (
        Transaction.objects.filter(buyer=request.user) | 
        Transaction.objects.filter(property__seller=request.user)
    ).select_related('property__seller', 'buyer', 'agent').order_by('-date')

    # Annotate each transaction with whether the user has rated it
    transactions_with_rating_status = []
    for transaction in transactions:
        # SELECT COUNT(*) FROM properties_agentrating 
        # WHERE transaction_id = <transaction.id> AND user_id = <request.user.id>;
        has_rated = transaction.ratings.filter(user=request.user).exists()
        transactions_with_rating_status.append({
            'transaction': transaction,
            'has_rated': has_rated
        })

    return render(request, 'user_transactions.html', {
        'transactions_with_rating_status': transactions_with_rating_status
    })

#=========USER INTERESTS============
@login_required
def user_interests(request):
    if request.user.role != 'normal':
        return redirect('home')
    # SELECT * FROM properties_interest WHERE interested_user_id = <request.user.id>;
    interests = Interest.objects.filter(interested_user=request.user).select_related('property')
    # SELECT property_id FROM properties_transaction WHERE buyer_id = <request.user.id> AND payment_status = 'approved';
    bought_properties = Transaction.objects.filter(
        buyer=request.user, payment_status='approved'
    ).values_list('property_id', flat=True)
    return render(
        request,
        'user_interests.html',
        {
            'interests': interests,
            'bought_properties': bought_properties
        }
    )
#=========AGENT PROPERTIES============
@login_required
def agent_properties(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'agent':
        messages.error(request, "Only agents can access this page.")
        return redirect('home')
    
    # SELECT DISTINCT p.* FROM properties_property p 
    # JOIN properties_interest i ON p.id = i.property_id 
    # WHERE i.assigned_agent_id = <request.user.id> AND i.status = 'assigned' AND p.status != 'sold';
    assigned_properties = Property.objects.filter(
        interest__assigned_agent=request.user,
        interest__status='assigned'
    ).exclude(status='sold').distinct()

    return render(request, 'agent_properties.html', {
        'assigned_properties': assigned_properties
    })

#=========AGENT TRANSACTIONS============
@login_required
def agent_transactions(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'agent':
        messages.error(request, "Only agents can access this page.")
        return redirect('home')
    
    # SELECT * FROM properties_transaction WHERE agent_id = <request.user.id> ORDER BY date DESC;
    transactions = Transaction.objects.filter(agent=request.user).order_by('-date')
    
    return render(request, 'agent_transactions.html', {'transactions': transactions})

#=========ADMIN PROPERTIES============
@login_required
def admin_properties(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('home')
    # SELECT * FROM properties_property;
    properties = Property.objects.all()
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        action = request.POST.get('action')
        # SELECT * FROM properties_property WHERE id = <property_id>;
        property = get_object_or_404(Property, id=property_id)
        if action == 'update_status':
            status = request.POST.get('status')
            if status in ['pending', 'approved', 'sold']:
                # SELECT EXISTS(SELECT 1 FROM properties_transaction WHERE property_id = <property.id>);
                if status == 'sold' and not Transaction.objects.filter(property=property).exists():
                    # SELECT i.* FROM properties_interest i WHERE i.property_id = <property.id> LIMIT 1;
                    interest = Interest.objects.filter(property=property).first()
                    if interest and property.assigned_agent:
                        # INSERT INTO properties_transaction (buyer_id, property_id, agent_id, amount, payment_status) 
                        # VALUES (<interest.interested_user.id>, <property.id>, <property.assigned_agent.id>, <property.price>, 'pending');
                        Transaction.objects.create(
                            buyer=interest.interested_user,
                            property=property,
                            agent=property.assigned_agent,
                            amount=property.price,
                            payment_status='pending'
                        )
                        property.assigned_agent = None
                        messages.success(request, "Property marked as sold. Transaction created.")
                    elif not property.assigned_agent:
                        messages.error(request, "Cannot mark as sold without an assigned agent.")
                        return redirect('admin_properties')
                property.status = status
                # UPDATE properties_property SET status = <status>, assigned_agent_id = NULL WHERE id = <property_id>;
                property.save()
                messages.success(request, f"Property status updated to {status}.")
        elif action == 'delete':
            # DELETE FROM properties_property WHERE id = <property_id>;
            property.delete()
            messages.success(request, "Property deleted successfully.")
        return redirect('admin_properties')
    return render(request, 'admin_properties.html', {'properties': properties})

#=========ADMIN PENDING PROPERTIES============
@login_required
def admin_pending_properties(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('home')
    # SELECT * FROM properties_property WHERE status = 'pending';
    pending_properties = Property.objects.filter(status='pending')
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        action = request.POST.get('action')
        # SELECT * FROM properties_property WHERE id = <property_id> AND status = 'pending';
        property = get_object_or_404(Property, id=property_id, status='pending')
        if action == 'approve':
            property.status = 'approved'
            # UPDATE properties_property SET status = 'approved' WHERE id = <property_id>;
            property.save()
            messages.success(request, "Property approved successfully.")
        elif action == 'reject':
            property.status = 'rejected'
            # UPDATE properties_property SET status = 'rejected' WHERE id = <property_id>;
            property.save()
            messages.success(request, "Property rejected successfully.")
        elif action == 'view_details':
            # Redirect to the admin_view_property view without modifying the property
            return redirect('admin_view_property', property_id=property_id)
        return redirect('admin_pending_properties')
    return render(request, 'admin_pending_properties.html', {'pending_properties': pending_properties})

#=========ADMIN AGENT REQUESTS============
@login_required
def admin_agent_requests(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('home')
    # SELECT * FROM properties_customuser WHERE agent_application_status = 'pending';
    agent_requests = CustomUser.objects.filter(agent_application_status='pending')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        # SELECT * FROM properties_customuser WHERE id = <user_id> AND agent_application_status = 'pending';
        user = get_object_or_404(CustomUser, id=user_id, agent_application_status='pending')
        if action == 'approve':
            user.role = 'agent'
            user.agent_application_status = 'approved'
            user.total_listings = 0
            user.average_rating = 0.0
            # UPDATE properties_customuser SET role = 'agent', agent_application_status = 'approved', 
            # total_listings = 0, average_rating = 0.0 WHERE id = <user_id>;
        elif action == 'reject':
            user.agent_application_status = 'rejected'
            # UPDATE properties_customuser SET agent_application_status = 'rejected' WHERE id = <user_id>;
        user.save()
        return redirect('admin_agent_requests')
    return render(request, 'admin_agent_requests.html', {'agent_requests': agent_requests})

#=========ADMIN INTERESTS============
@login_required
def admin_interests(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('home')
    # SELECT * FROM properties_interest WHERE assigned_agent_id IS NULL;
    unassigned_interests = Interest.objects.filter(assigned_agent__isnull=True)
    # SELECT u.*, COUNT(p.id) as active_properties 
    # FROM properties_customuser u 
    # LEFT JOIN properties_property p ON u.id = p.assigned_agent_id 
    # WHERE u.role = 'agent' AND (p.status IN ('pending', 'approved') OR p.id IS NULL) 
    # GROUP BY u.id HAVING active_properties < 5;
    agents = CustomUser.objects.filter(
        role='agent'
    ).annotate(
        active_properties=models.Count('assigned_properties', filter=models.Q(assigned_properties__status__in=['pending', 'approved']))
    ).filter(active_properties__lt=5)
    if request.method == 'POST':
        interest_id = request.POST.get('interest_id')
        agent_id = request.POST.get('agent_id')
        # SELECT * FROM properties_interest WHERE id = <interest_id> AND assigned_agent_id IS NULL;
        interest = get_object_or_404(Interest, id=interest_id, assigned_agent__isnull=True)
        # SELECT * FROM properties_customuser WHERE id = <agent_id> AND role = 'agent';
        agent = get_object_or_404(CustomUser, id=agent_id, role='agent')
        # SELECT COUNT(*) FROM properties_property WHERE assigned_agent_id = <agent.id> AND status IN ('pending', 'approved');
        if Property.objects.filter(assigned_agent=agent, status__in=['pending', 'approved']).count() < 5:
            interest.assigned_agent = agent
            interest.property.assigned_agent = agent
            interest.status = 'assigned'
            # UPDATE properties_interest SET assigned_agent_id = <agent.id>, status = 'assigned' WHERE id = <interest_id>;
            interest.save()
            # UPDATE properties_property SET assigned_agent_id = <agent.id> WHERE id = <interest.property.id>;
            interest.property.save()
            messages.success(request, "Agent assigned successfully.")
        else:
            messages.error(request, "Selected agent has reached the maximum of 5 active properties.")
        return redirect('admin_interests')
    return render(request, 'admin_interests.html', {'unassigned_interests': unassigned_interests, 'agents': agents})

#=========ADMIN TRANSACTIONS============
@login_required
def admin_transactions(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can access this page.")
        return redirect('home')
    
    # SELECT t.*, p.*, a.*, b.* FROM properties_transaction t 
    # JOIN properties_property p ON t.property_id = p.id 
    # LEFT JOIN properties_customuser a ON t.agent_id = a.id 
    # JOIN properties_customuser b ON t.buyer_id = b.id 
    # ORDER BY t.date DESC;
    transactions = Transaction.objects.all().select_related('property', 'agent', 'buyer').order_by('-date')
    
    context = {'transactions': transactions}
    return render(request, 'admin_transactions.html', context)

#=========ADMIN VIEW PROPERTY============
@login_required
def admin_view_property(request, property_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('home')
    # SELECT * FROM properties_property WHERE id = <property_id>;
    property = get_object_or_404(Property, id=property_id)
    return render(request, 'property_detail.html', {'property': property})

#=========EDIT PROPERTY============
@login_required
def edit_property(request, property_id):
    # SELECT * FROM properties_property WHERE id = <property_id> AND seller_id = <request.user.id>;
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    # SELECT status FROM properties_property WHERE id = <property_id>;
    if property.status == 'sold':
        messages.error(request, "Cannot edit a sold property.")
        return redirect('user_properties')
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property)
        if form.is_valid():
            updated_property = form.save(commit=False)
            updated_property.status = 'pending'
            # UPDATE properties_property SET status = 'pending', title = <form.cleaned_data['title']>, 
            # description = <form.cleaned_data['description']>, price = <form.cleaned_data['price']>, ... 
            # WHERE id = <property_id>;
            updated_property.save()
            messages.success(request, "Property updated and submitted for admin approval.")
            return redirect('user_properties')
    else:
        form = PropertyForm(instance=property)
    return render(request, 'edit_property.html', {'form': form, 'property': property})

#=========DELETE PROPERTY============
@login_required
def delete_property(request, property_id):
    # SELECT * FROM properties_property WHERE id = <property_id> AND seller_id = <request.user.id>;
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    # SELECT status FROM properties_property WHERE id = <property_id>;
    if property.status == 'sold':
        messages.error(request, "Cannot delete a sold property.")
        return redirect('user_properties')
    if request.method == 'POST':
        # DELETE FROM properties_property WHERE id = <property_id>;
        property.delete()
        messages.success(request, "Property deleted successfully.")
        return redirect('user_properties')
    return render(request, 'delete_property.html', {'property': property})

#=========VIEW PROPERTY============
@login_required
def view_property(request, property_id):
    # SELECT * FROM properties_property WHERE id = <property_id> AND seller_id = <request.user.id>;
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    return render(request, 'property_detail.html', {'property': property})
#=========ADMIN AGENT ASSIGNMENTS============
@login_required
def admin_agent_assignments(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        return redirect('home')
    # SELECT u.*, COUNT(p.id) as active_properties 
    # FROM properties_customuser u 
    # LEFT JOIN properties_property p ON u.id = p.assigned_agent_id 
    # WHERE u.role = 'agent' AND (p.status IN ('pending', 'approved') OR p.id IS NULL) 
    # GROUP BY u.id;
    agents = CustomUser.objects.filter(role='agent').annotate(
        active_properties=models.Count('properties', filter=models.Q(properties__status__in=['pending', 'approved']))
    )
    # New: Attach filtered properties to each agent object
    for agent in agents:
        # SELECT * FROM properties_property WHERE assigned_agent_id = <agent.id> AND status IN ('pending', 'approved');
        agent.active_property_list = agent.properties.filter(status__in=['pending', 'approved'])
    return render(request, 'admin_agent_assignments.html', {'agents': agents})

#=========REMOVE INTEREST============
@login_required
def remove_interest(request, property_id):
    # Only normal users can remove their own interests
    if request.user.role != 'normal':
        messages.error(request, "Only normal users can remove interests.")
        return redirect('user_interests')

    # Try to find the interest for this user and property
    try:
        interest = Interest.objects.get(property__id=property_id, interested_user=request.user)
        # DELETE FROM properties_interest WHERE property_id = <property_id> AND interested_user_id = <request.user.id>;
        interest.delete()
        messages.success(request, "Interest removed successfully.")
    except Interest.DoesNotExist:
        # If no interest exists (possibly because the property was deleted), inform the user
        messages.warning(request, "The property no longer exists or you haven't expressed interest in it.")
    except Property.DoesNotExist:
        # This case is unlikely since we're querying Interest, but handle it just in case
        messages.warning(request, "The property no longer exists.")

    return redirect('user_interests')
#=========REQUEST TRANSACTION============
@login_required
def request_transaction(request, property_id):
    if request.user.role != 'agent':
        messages.error(request, "Only agents can request transactions.")
        return redirect('home')
    
    property = get_object_or_404(Property, id=property_id, assigned_agent=request.user)
    if property.status == 'sold':
        messages.error(request, "This property is already sold.")
        return redirect('agent_properties')
    
    if Transaction.objects.filter(property=property, payment_status='pending').exists():
        messages.error(request, "A pending transaction already exists for this property.")
        return redirect('agent_properties')
    
    if request.method == 'POST':
        buyer_id = request.POST.get('buyer_id')
        amount = request.POST.get('amount')
        
        buyer = get_object_or_404(CustomUser, id=buyer_id)
        
        try:
            amount = float(amount) if amount else None
            if amount is None:
                raise ValueError("Amount is required.")
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            if amount > 9999999999.99:
                raise ValueError("Amount exceeds maximum allowed value (9999999999.99).")
        except (ValueError, TypeError) as e:
            # logger.error(f"Invalid amount for property {property_id}: {amount}, error: {str(e)}")
            messages.error(request, f"Invalid amount: {str(e)}")
            interested_users = Interest.objects.filter(property=property, assigned_agent=request.user, status='assigned')
            return render(request, 'request_transaction.html', {
                'property': property,
                'interested_users': interested_users
            })
        
        # logger.debug(f"Creating transaction for property {property_id} with amount: {amount}")
        
        transaction = Transaction.objects.create(
            buyer=buyer,
            property=property,
            agent=request.user,
            amount=amount,
            payment_status='pending'
        )
        
        messages.info(
            request,
            f"Transaction request for '{property.title}': Agent: {request.user.username}, Buyer: {buyer.username}, Seller: {property.seller.username}, Amount: ${amount}",
            extra_tags='admin_transaction'
        )
        messages.success(request, "Transaction request submitted to admin.")
        return redirect('agent_properties')
    
    interested_users = Interest.objects.filter(property=property, assigned_agent=request.user, status='assigned')
    return render(request, 'request_transaction.html', {
        'property': property,
        'interested_users': interested_users
    })

#=========ADMIN CONFIRM TRANSACTION============
@login_required
def admin_confirm_transaction(request, transaction_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can confirm transactions.")
        return redirect('home')

    # SELECT * FROM properties_transaction WHERE id = <transaction_id> AND payment_status = 'pending';
    transaction = get_object_or_404(Transaction, id=transaction_id, payment_status='pending')
    if request.method == 'POST':
        transaction.payment_status = 'approved'
        transaction.property.status = 'sold'
        # UPDATE properties_property SET status = 'sold' WHERE id = <transaction.property.id>;
        transaction.property.save()
        # UPDATE properties_transaction SET payment_status = 'approved' WHERE id = <transaction_id>;
        transaction.save()
        messages.success(request, f"Transaction for '{transaction.property.title}' confirmed.")
        return redirect('admin_pending_transactions')

    return render(request, 'admin_confirm_transaction.html', {'transaction': transaction})

#=========PROPERTY DETAILS AGENT============
@login_required
def property_details_agent(request, property_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'agent':
        messages.error(request, "Only agents can access this page.")
        return redirect('home')
    
    # SELECT p.* FROM properties_property p 
    # JOIN properties_interest i ON p.id = i.property_id 
    # WHERE p.id = <property_id> AND i.assigned_agent_id = <request.user.id>;
    property = get_object_or_404(Property.objects.filter(id=property_id, interest__assigned_agent=request.user).distinct())
    # SELECT * FROM properties_interest WHERE property_id = <property.id> AND assigned_agent_id = <request.user.id> AND status = 'assigned';
    interests = Interest.objects.filter(property=property, assigned_agent=request.user, status='assigned')
    # SELECT * FROM properties_transaction WHERE property_id = <property.id> AND agent_id = <request.user.id> LIMIT 1;
    transaction = Transaction.objects.filter(property=property, agent=request.user).first()

    if request.method == 'POST' and not transaction:
        buyer_id = request.POST.get('buyer_id')
        selling_price = request.POST.get('selling_price')
        # SELECT * FROM properties_customuser WHERE id = <buyer_id>;
        buyer = get_object_or_404(CustomUser, id=buyer_id)
        
        # INSERT INTO properties_transaction (property_id, agent_id, buyer_id, amount, payment_status) 
        # VALUES (<property.id>, <request.user.id>, <buyer.id>, <selling_price>, 'pending');
        Transaction.objects.create(
            property=property,
            agent=request.user,
            buyer=buyer,
            amount=selling_price,
            payment_status='pending'
        )
        messages.success(request, f"Transaction request sent for '{property.title}'.")
        return redirect('property_details_agent', property_id=property_id)

    return render(request, 'property_details_agent.html', {
        'property': property,
        'interests': interests,
        'transaction': transaction
    })


#=========TRANSACTION DETAIL============
@login_required
def transaction_detail(request, transaction_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'agent':
        messages.error(request, "Only agents can access this page.")
        return redirect('home')
    
    # SELECT t.* FROM properties_transaction t 
    # JOIN properties_property p ON t.property_id = p.id 
    # WHERE t.id = <transaction_id> AND t.agent_id = <request.user.id> 
    # AND t.payment_status = 'approved' AND p.status = 'sold';
    transaction = get_object_or_404(Transaction, id=transaction_id, agent=request.user, payment_status='approved', property__status='sold')
    
    return render(request, 'transaction_detail.html', {'transaction': transaction})

#=========ADMIN TRANSACTION DETAIL============
@login_required
def admin_transaction_detail(request, transaction_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can access this page.")
        return redirect('home')
    
    # SELECT * FROM properties_transaction WHERE id = <transaction_id>;
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    return render(request, 'admin_transaction_detail.html', {'transaction': transaction})

#=========ADMIN PENDING TRANSACTIONS============
@login_required
def admin_pending_transactions(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can access this page.")
        return redirect('home')
    
    # SELECT t.*, p.*, a.*, b.* FROM properties_transaction t 
    # JOIN properties_property p ON t.property_id = p.id 
    # LEFT JOIN properties_customuser a ON t.agent_id = a.id 
    # JOIN properties_customuser b ON t.buyer_id = b.id 
    # WHERE t.payment_status = 'pending' 
    # ORDER BY t.date DESC;
    pending_transactions = Transaction.objects.filter(payment_status='pending').select_related('property', 'agent', 'buyer').order_by('-date')
    
    context = {'pending_transactions': pending_transactions}
    return render(request, 'admin_pending_transactions.html', context)

#=========ADMIN FEEDBACKS============
@login_required
def admin_feedbacks(request):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can access this page.")
        return redirect('home')
    
    # SELECT f.*, u.* FROM properties_feedback f 
    # JOIN properties_customuser u ON f.user_id = u.id 
    # ORDER BY f.date DESC;
    feedbacks = Feedback.objects.all().select_related('user').order_by('-date')
    
    return render(request, 'admin_feedbacks.html', {'feedbacks': feedbacks})

#=========MARK FEEDBACK READ============
@login_required
def mark_feedback_read(request, feedback_id):
    # SELECT role FROM properties_customuser WHERE id = <request.user.id>;
    if request.user.role != 'admin':
        messages.error(request, "Only admins can mark feedback as read.")
        return redirect('home')
    
    # SELECT * FROM properties_feedback WHERE id = <feedback_id>;
    feedback = get_object_or_404(Feedback, id=feedback_id)
    if request.method == 'POST':
        feedback.status = 'read'
        # UPDATE properties_feedback SET status = 'read' WHERE id = <feedback_id>;
        feedback.save()
        messages.success(request, "Feedback marked as read.")
        return redirect('admin_feedbacks')
    return redirect('admin_feedbacks')


#=========SUBMIT RATING============
#=========SUBMIT RATING============
@login_required
def submit_rating(request, transaction_id):
    # SELECT * FROM properties_transaction WHERE id = <transaction_id>;
    transaction = get_object_or_404(Transaction, id=transaction_id, payment_status='approved')
    
    # Determine rater type and validate eligibility
    rater_type = None
    if request.user == transaction.buyer:
        rater_type = 'buyer'
    elif request.user == transaction.property.seller:
        rater_type = 'seller'
    else:
        messages.error(request, "You are not eligible to rate this transaction.")
        return redirect('user_transactions')
    
    if request.user == transaction.agent:
        messages.error(request, "Agents cannot rate themselves.")
        return redirect('user_transactions')
    
    # Check if the user already rated this transaction
    # SELECT COUNT(*) FROM properties_agentrating 
    # WHERE transaction_id = <transaction.id> AND user_id = <request.user.id>;
    if AgentRating.objects.filter(transaction=transaction, user=request.user).exists():
        messages.error(request, "You have already rated this transaction.")
        return redirect('user_transactions')
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        review = request.POST.get('review', '')
        if 1 <= rating <= 5:
            # INSERT INTO properties_agentrating (user_id, agent_id, rating, review, date, transaction_id)
            # VALUES (<request.user.id>, <transaction.agent.id>, <rating>, <review>, NOW(), <transaction.id>);
            AgentRating.objects.create(
                user=request.user,
                agent=transaction.agent,
                rating=rating,
                review=review,
                transaction=transaction
            )
            messages.success(request, "Rating submitted successfully.")
            return redirect('user_transactions')
        messages.error(request, "Please select a valid rating (1-5 stars).")
    
    return render(request, 'submit_rating.html', {'transaction': transaction})

#=========AGENT RATINGS============
@login_required
def agent_ratings(request):
    if request.user.role != 'agent':
        messages.error(request, "Only agents can access this page.")
        return redirect('home')
    
    # SELECT * FROM properties_agentrating WHERE agent_id = <request.user.id>;
    ratings = AgentRating.objects.filter(agent=request.user).select_related('transaction__property', 'user')
    
    # Sorting
    sort_by = request.GET.get('sort', 'date_desc')
    if sort_by == 'rating_asc':
        ratings = ratings.order_by('rating')
    elif sort_by == 'rating_desc':
        ratings = ratings.order_by('-rating')
    else:  # Default: date_desc
        ratings = ratings.order_by('-date')
    
    # Pagination
    paginator = Paginator(ratings, 10)  # 10 ratings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Annotate ratings with rater type
    ratings_with_rater_type = []
    for rating in page_obj:
        rater_type = 'Unknown'
        if rating.user == rating.transaction.buyer:
            rater_type = 'Buyer'
        elif rating.user == rating.transaction.property.seller:
            rater_type = 'Seller'
        ratings_with_rater_type.append({
            'rating': rating,
            'rater_type': rater_type
        })
    
    return render(request, 'agent_ratings.html', {
        'page_obj': page_obj,
        'ratings_with_rater_type': ratings_with_rater_type,
        'average_rating': request.user.average_rating or 0.0,
        'sort_by': sort_by,
    })

#=========ADMIN REJECT TRANSACTION============
@login_required
def admin_reject_transaction(request, transaction_id):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can reject transactions.")
        return redirect('home')
    
    try:
        transaction = Transaction.objects.get(id=transaction_id, payment_status='pending')
    except Transaction.DoesNotExist:
        messages.error(request, "Transaction not found or already processed.")
        return redirect('admin_pending_transactions')
    
    
    
    transaction.payment_status = 'rejected'
    transaction.save()
    
    transaction.property.status = 'approved'
    transaction.property.save()
    

    
    messages.success(request, "Transaction rejected successfully. The agent can submit a new request.")
    return redirect('admin_pending_transactions')