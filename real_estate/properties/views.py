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

def about_us(request):
    return render(request, 'about_us.html')

def home(request):
    # Base query excludes sold properties for all users
    properties = Property.objects.exclude(status='sold')
    interested_property_ids = set()
    
    if request.user.is_authenticated:
        # Exclude user's own listings and get interested property IDs
        properties = properties.exclude(seller=request.user)
        interested_property_ids = set(request.user.interests.values_list('property_id', flat=True))
    # Else: Unauthenticated users see all non-sold properties (no further filtering)

    # Search and filter logic
    query = request.GET.get('q', '')
    property_type = request.GET.get('property_type', '')
    city = request.GET.get('city', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    bedrooms = request.GET.get('bedrooms', '')

    if query:
        properties = properties.filter(
            models.Q(title__icontains=query) |
            models.Q(description__icontains=query)
        )
    if property_type:
        properties = properties.filter(property_type=property_type)
    if city:
        properties = properties.filter(city__icontains=city)
    if min_price:
        properties = properties.filter(price__gte=min_price)
    if max_price:
        properties = properties.filter(price__lte=max_price)
    if bedrooms:
        properties = properties.filter(bedrooms__gte=bedrooms)

    return render(request, 'home.html', {
        'properties': properties,
        'interested_property_ids': interested_property_ids
    })

def normal_signup(request):
    if request.method == 'POST':
        form = NormalUserSignUpForm(request.POST)
        if form.is_valid():
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

@login_required
def dashboard(request):
    if request.user.role == 'normal':
        return user_dashboard(request)
    elif request.user.role == 'agent':
        return agent_dashboard(request)
    elif request.user.role == 'admin':
        return admin_dashboard(request)
    return redirect('home')


@login_required
def user_dashboard(request):
    properties = Property.objects.filter(seller=request.user)
    transactions = Transaction.objects.filter(buyer=request.user)
    interests = Interest.objects.filter(interested_user=request.user)
    feedbacks = Feedback.objects.filter(user=request.user) if 'Feedback' in globals() else []
    context = {
        'properties': properties,
        'transactions': transactions,
        'interests': interests,
        'feedbacks': feedbacks,
    }
    return render(request, 'user_dashboard.html', context)


@login_required
def agent_dashboard(request):
    if request.user.role != 'agent':
        return redirect('dashboard')
    properties = Property.objects.filter(assigned_agent=request.user)
    transactions = Transaction.objects.filter(agent=request.user)
    interests = Interest.objects.filter(assigned_agent=request.user)
    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id')
        transaction = get_object_or_404(Transaction, id=transaction_id, agent=request.user)
        transaction.payment_status = 'approved'
        transaction.save()
        request.user.total_listings += 1
        request.user.save()
    context = {
        'properties': properties,
        'transactions': transactions,
        'interests': interests,
    }
    return render(request, 'agent_dashboard.html', context)

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    properties = Property.objects.all()
    pending_properties = Property.objects.filter(status='pending')
    agent_requests = CustomUser.objects.filter(agent_application_status='pending')
    transactions = Transaction.objects.all()
    unassigned_interests = Interest.objects.filter(assigned_agent__isnull=True)  # Notify admin
    agents = CustomUser.objects.filter(role='agent')
    if request.method == 'POST':
        interest_id = request.POST.get('interest_id')
        agent_id = request.POST.get('agent_id')
        interest = get_object_or_404(Interest, id=interest_id, assigned_agent__isnull=True)
        agent = get_object_or_404(CustomUser, id=agent_id, role='agent')
        interest.assigned_agent = agent
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

#USER DETAIL
@login_required
def user_detail(request, user_id):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can view user details.")
        return redirect('dashboard')
    user = get_object_or_404(CustomUser, id=user_id)
    if user.role == 'admin':
        messages.error(request, "Admins cannot view other admin details here.")
        return redirect('manage_users')
    return render(request, 'user_detail.html', {'user': user})
#EDIT USER
@login_required
def edit_user(request, user_id):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can edit users.")
        return redirect('dashboard')
    user = get_object_or_404(CustomUser, id=user_id)
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
            form.save()
            user.save()
            messages.success(request, f"User {user.username} updated successfully.")
            return redirect('manage_users')
    else:
        form = UserProfileForm(instance=user)
    return render(request, 'edit_user.html', {'form': form, 'user': user})

#DELETE USER
@login_required
def delete_user(request, user_id):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can delete users.")
        return redirect('dashboard')
    user = get_object_or_404(CustomUser, id=user_id)
    if user.role == 'admin':
        messages.error(request, "Admins cannot delete other admins.")
        return redirect('manage_users')
    if request.method == 'POST':
        user.delete()
        messages.success(request, f"User {user.username} deleted successfully.")
        return redirect('manage_users')
    return render(request, 'delete_user.html', {'user': user})



login_required
def create_property(request):
    ImageFormSet = modelformset_factory(PropertyImage, form=PropertyImageForm, extra=3)  # 3 extra image fields
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        formset = ImageFormSet(request.POST, request.FILES, queryset=PropertyImage.objects.none())
        if form.is_valid() and formset.is_valid():
            property = form.save(commit=False)
            property.seller = request.user
            property.status = 'pending'
            property.save()
            for image_form in formset:
                if image_form.cleaned_data.get('image'):  # Only save if an image is provided
                    PropertyImage.objects.create(property=property, image=image_form.cleaned_data['image'])
            messages.success(request, "Property listed successfully. Awaiting admin approval.")
            return redirect('dashboard')
    else:
        form = PropertyForm()
        formset = ImageFormSet(queryset=PropertyImage.objects.none())
    return render(request, 'create_property.html', {'form': form, 'formset': formset})

#EDIT PROPERTY
@login_required
def edit_property(request, property_id):
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=property)
        images = request.FILES.getlist('images')
        if form.is_valid():
            property = form.save(commit=False)
            property.status = 'under_review'
            property.save()
            for image in images:
                PropertyImage.objects.create(property=property, image=image)
            messages.success(request, "Property updated and under review.")
            return redirect('dashboard')
    else:
        form = PropertyForm(instance=property)
    return render(request, 'edit_property.html', {'form': form, 'property': property})
#DELETE PROPERTY
@login_required
def delete_property(request, property_id):
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    if request.method == 'POST':
        property.delete()
        messages.success(request, "Property deleted.")
        return redirect('dashboard')
    return render(request, 'delete_property.html', {'property': property})

@login_required
def property_detail(request, property_id):
    property = get_object_or_404(Property, id=property_id)
    return render(request, 'property_detail.html', {'property': property})

# properties/views.py
@login_required
def express_interest(request, property_id):
    if request.user.role != 'normal':
        return redirect('home')
    property = get_object_or_404(Property, id=property_id, status='approved')
    if request.user == property.seller:
        messages.error(request, "You cannot express interest in your own property.")
        return redirect('home')
    if not Interest.objects.filter(property=property, interested_user=request.user).exists():
        Interest.objects.create(
            property=property,
            interested_user=request.user,
            assigned_agent=None,  # No agent assigned here
            status='pending'  # Stays pending until "Contact an Agent"
        )
        # Updated: Notify admin of interest without agent assignment
        messages.info(request, f"User {request.user.username} expressed interest in '{property.title}' (ID: {property.id}).", extra_tags='admin_notification')
        messages.success(request, "Interest expressed successfully.")
    return redirect('user_interests')

# New: Handle contact agent request
@login_required
def contact_agent(request, interest_id):
    if request.user.role != 'normal':
        return redirect('home')
    interest = get_object_or_404(Interest, id=interest_id, interested_user=request.user)
    if interest.assigned_agent is None and interest.status != 'assigning':
        interest.status = 'assigning'  # New: Change status to "Assigning…"
        interest.save()
        messages.success(request, "An agent will contact you shortly.")
    return redirect('user_interests')

@login_required
def submit_feedback(request):
    if request.user.role != 'normal':
        messages.error(request, "Only normal users can submit feedback.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.save()
            messages.success(request, "Feedback submitted.")
            return redirect('dashboard')
    else:
        form = FeedbackForm()
    return render(request, 'feedback.html', {'form': form})

#UPDATE PROFILE
@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('dashboard')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'update_profile.html', {'form': form})

#MANGE USERS
@login_required
def manage_users(request):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can manage users.")
        return redirect('dashboard')
    users = CustomUser.objects.exclude(role='admin')
    roles = ['normal', 'agent']  # Only normal and agent roles
    return render(request, 'manage_users.html', {'users': users, 'roles': roles})

@login_required
def approve_property(request, property_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    property = get_object_or_404(Property, id=property_id)
    property.status = 'approved'
    property.save()
    messages.success(request, f"Property '{property.title}' approved.")
    return redirect('dashboard')

@login_required
def mark_sold(request, property_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    property = get_object_or_404(Property, id=property_id)
    if request.method == 'POST':
        buyer_id = request.POST['buyer']
        buyer = get_object_or_404(CustomUser, id=buyer_id)
        Transaction.objects.create(property=property, buyer=buyer, seller=property.seller, amount=property.price)
        property.status = 'sold'
        property.save()
        messages.success(request, f"Property '{property.title}' marked as sold.")
    return redirect('dashboard')

@login_required
def create_admin(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        form = AdminCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Admin created.")
            return redirect('manage_users')
    else:
        form = AdminCreationForm()
    return render(request, 'create_admin.html', {'form': form})


@login_required
def remove_admin(request, user_id):
    if request.user.role != 'admin' or request.user.id == user_id:
        return redirect('dashboard')
    user = get_object_or_404(CustomUser, id=user_id, role='admin')
    user.delete()
    messages.success(request, f"Admin '{user.username}' removed.")
    return redirect('dashboard')

@login_required
def admin_edit_property(request, property_id):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can edit properties.")
        return redirect('dashboard')
    property = get_object_or_404(Property, id=property_id)
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=property)
        images = request.FILES.getlist('images')
        if form.is_valid():
            property = form.save()
            for image in images:
                PropertyImage.objects.create(property=property, image=image)
            messages.success(request, f"Property '{property.title}' updated successfully.")
            return redirect('admin_dashboard')  # Updated to use URL name
    else:
        form = PropertyForm(instance=property)
    return render(request, 'admin_edit_property.html', {'form': form, 'property': property})

@login_required
def admin_delete_property(request, property_id):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can delete properties.")
        return redirect('dashboard')
    property = get_object_or_404(Property, id=property_id)
    if request.method == 'POST':
        property.delete()
        messages.success(request, f"Property '{property.title}' deleted successfully.")
        return redirect('admin_dashboard')  # Updated to use URL name
    return render(request, 'admin_delete_property.html', {'property': property})


@login_required
def apply_agent(request):
    if request.user.role != 'normal' or request.user.agent_application_status != 'none':
        return render(request, 'apply_agent_error.html', {'message': 'You cannot apply as an agent at this time.'})
    if request.method == 'POST':
        form = AgentApplicationForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.agent_application_status = 'pending'
            user.save()
            return render(request, 'apply_agent_success.html')
        return render(request, 'apply_agent.html', {'form': form, 'error': 'Please correct the errors below.'})
    form = AgentApplicationForm(instance=request.user)
    return render(request, 'apply_agent.html', {'form': form})

@login_required
def approve_agent(request, user_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    user = get_object_or_404(CustomUser, id=user_id, agent_application_status='pending')
    user.role = 'agent'
    user.agent_application_status = 'approved'
    user.total_listings = 0  # Initialize agent stats
    user.average_rating = 0.0
    user.save()
    return redirect('admin_dashboard')

@login_required
def reject_agent(request, user_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    user = get_object_or_404(CustomUser, id=user_id, agent_application_status='pending')
    user.agent_application_status = 'rejected'
    user.save()
    return redirect('admin_dashboard')

#RATE AGENT
@login_required
def rate_agent(request, agent_id):
    agent = get_object_or_404(CustomUser, id=agent_id, role='agent')
    if request.user.role != 'normal':
        messages.error(request, "Only normal users can rate agents.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = AgentRatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.user = request.user
            rating.agent = agent
            rating.save()
            messages.success(request, "Rating submitted.")
            return redirect('dashboard')
    else:
        form = AgentRatingForm()
    return render(request, 'rate_agent.html', {'form': form, 'agent': agent})

@login_required
def agent_transactions(request):
    if request.user.role != 'agent':
        return redirect('dashboard')
    transactions = Transaction.objects.filter(agent=request.user)
    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id')
        transaction = get_object_or_404(Transaction, id=transaction_id, agent=request.user)
        transaction.payment_status = 'approved'
        transaction.save()
        request.user.total_listings += 1  # Increment agent's listings
        request.user.save()
    return render(request, 'agent_transactions.html', {'transactions': transactions})

@login_required
def confirm_transaction(request, property_id):
    property = get_object_or_404(Property, id=property_id, assigned_agent=request.user)
    if request.user.role != 'agent':
        messages.error(request, "Only agents can confirm transactions.")
        return redirect('dashboard')
    if request.method == 'POST':
        buyer_id = request.POST['buyer']
        buyer = get_object_or_404(CustomUser, id=buyer_id)
        commission = property.price * (property.commission_rate / 100)
        Transaction.objects.create(
            property=property, buyer=buyer, agent=request.user,
            amount=property.price, commission=commission
        )
        property.status = 'sold'
        property.save()
        request.user.total_listings += 1
        request.user.save()
        messages.success(request, "Transaction confirmed.")
        return redirect('dashboard')
    return render(request, 'confirm_transaction.html', {'property': property})

#USER_LISTING
@login_required
def user_listings(request):
    if request.user.role != 'normal':
        return redirect('dashboard')
    properties = Property.objects.filter(seller=request.user)
    return render(request, 'user_listings.html', {'properties': properties})

#AGENT_LISTING
# properties/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Property, Interest, Transaction

# properties/views.py
@login_required
def agent_interests(request):
    if request.user.role != 'agent':
        return redirect('home')
    properties = Property.objects.filter(assigned_agent=request.user, interest__isnull=False).distinct()
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        status = request.POST.get('status')
        property = get_object_or_404(Property, id=property_id, assigned_agent=request.user)
        if property.status == 'sold':
            messages.error(request, "Cannot change status of a sold property.")
            return redirect('agent_interests')
        # Changed: Restrict 'sold' update, limit to 'pending' or 'approved'
        if status in ['pending', 'approved']:
            property.status = status
            property.save()
            messages.success(request, f"Property status updated to {status}.")
        return redirect('agent_interests')
    return render(request, 'agent_interests.html', {'properties': properties})

# properties/views.py
@login_required
def update_property_status(request, property_id):
    property = get_object_or_404(Property, id=property_id)
    if request.user.role not in ['agent', 'admin'] or (request.user.role == 'agent' and property.assigned_agent != request.user):
        return render(request, 'error.html', {'message': 'You are not authorized to update this property.'})
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['pending', 'approved', 'sold']:
            property.status = status
            property.save()
            if status == 'sold' and request.user.role == 'agent':
                Transaction.objects.create(
                    buyer=Interest.objects.filter(property=property).first().interested_user,
                    property=property,
                    agent=request.user,
                    amount=property.price
                )
            return redirect('dashboard')
    return render(request, 'update_property_status.html', {'property': property})

# Normal User Views
@login_required
def user_properties(request):
    if request.user.role != 'normal':
        return redirect('home')
    properties = Property.objects.filter(seller=request.user)
    return render(request, 'user_properties.html', {'properties': properties})

@login_required
def user_transactions(request):
    if request.user.role != 'normal':
        return redirect('home')
    # Changed: Include transactions where user is seller or buyer for sold properties
    transactions = Transaction.objects.filter(buyer=request.user) | Transaction.objects.filter(property__seller=request.user)
    return render(request, 'user_transactions.html', {'transactions': transactions})

@login_required
def user_interests(request):
    if request.user.role != 'normal':
        return redirect('home')
    interests = Interest.objects.filter(interested_user=request.user)
    return render(request, 'user_interests.html', {'interests': interests})


# Agent Views
@login_required
def agent_properties(request):
    if request.user.role != 'agent':
        messages.error(request, "Only agents can access this page.")
        return redirect('home')
    
    # Get properties assigned to this agent with interested users
    assigned_properties = Property.objects.filter(
        interest__assigned_agent=request.user,
        interest__status='assigned'
    ).distinct()

    if request.method == 'POST':
        # Updated: Remove user from interest list
        interest_id = request.POST.get('interest_id')
        interest = get_object_or_404(Interest, id=interest_id, assigned_agent=request.user)
        property_title = interest.property.title
        interest.delete()  # Removes from agent's view and user's interest list
        messages.success(request, f"Removed interest for '{property_title}'.")
        return redirect('agent_properties')

    return render(request, 'agent_properties.html', {
        'assigned_properties': assigned_properties
    })


@login_required
def agent_transactions(request):
    if request.user.role != 'agent':
        return redirect('home')
    transactions = Transaction.objects.filter(agent=request.user) | Transaction.objects.filter(property__assigned_agent=request.user, property__status='sold')
    return render(request, 'agent_transactions.html', {'transactions': transactions})

#Admin Views
@login_required
def admin_properties(request):
    if request.user.role != 'admin':
        return redirect('home')
    properties = Property.objects.all()
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        action = request.POST.get('action')
        property = get_object_or_404(Property, id=property_id)
        if action == 'update_status':
            status = request.POST.get('status')
            if status in ['pending', 'approved', 'sold']:
                if status == 'sold' and not Transaction.objects.filter(property=property).exists():
                    interest = Interest.objects.filter(property=property).first()
                    if interest and property.assigned_agent:
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
                property.save()
                messages.success(request, f"Property status updated to {status}.")
        elif action == 'delete':
            property.delete()
            messages.success(request, "Property deleted successfully.")
        return redirect('admin_properties')
    return render(request, 'admin_properties.html', {'properties': properties})

@login_required
def admin_pending_properties(request):
    if request.user.role != 'admin':
        return redirect('home')
    pending_properties = Property.objects.filter(status='pending')
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        property = get_object_or_404(Property, id=property_id, status='pending')
        property.status = 'approved'
        property.save()
        messages.success(request, "Property approved successfully.")
        return redirect('admin_pending_properties')
    return render(request, 'admin_pending_properties.html', {'pending_properties': pending_properties})

@login_required
def admin_agent_requests(request):
    if request.user.role != 'admin':
        return redirect('home')
    agent_requests = CustomUser.objects.filter(agent_application_status='pending')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = get_object_or_404(CustomUser, id=user_id, agent_application_status='pending')
        if action == 'approve':
            user.role = 'agent'
            user.agent_application_status = 'approved'
            user.total_listings = 0
            user.average_rating = 0.0
        elif action == 'reject':
            user.agent_application_status = 'rejected'
        user.save()
        return redirect('admin_agent_requests')
    return render(request, 'admin_agent_requests.html', {'agent_requests': agent_requests})

@login_required
def admin_interests(request):
    if request.user.role != 'admin':
        return redirect('home')
    unassigned_interests = Interest.objects.filter(assigned_agent__isnull=True)
    agents = CustomUser.objects.filter(
        role='agent'
    ).annotate(
        active_properties=models.Count('assigned_properties', filter=models.Q(assigned_properties__status__in=['pending', 'approved']))
    ).filter(active_properties__lt=5)
    if request.method == 'POST':
        interest_id = request.POST.get('interest_id')
        agent_id = request.POST.get('agent_id')
        interest = get_object_or_404(Interest, id=interest_id, assigned_agent__isnull=True)
        agent = get_object_or_404(CustomUser, id=agent_id, role='agent')
        if Property.objects.filter(assigned_agent=agent, status__in=['pending', 'approved']).count() < 5:
            interest.assigned_agent = agent
            interest.property.assigned_agent = agent
            interest.status = 'assigned'  # New: Update status to "Assigned"
            interest.save()
            interest.property.save()
            messages.success(request, "Agent assigned successfully.")
        else:
            messages.error(request, "Selected agent has reached the maximum of 5 active properties.")
        return redirect('admin_interests')
    return render(request, 'admin_interests.html', {'unassigned_interests': unassigned_interests, 'agents': agents})

@login_required
def admin_transactions(request):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can view this page.")
        return redirect('home')
    
    transactions = Transaction.objects.filter(payment_status='pending')
    return render(request, 'admin_transactions.html', {'transactions': transactions})

@login_required
def admin_view_property(request, property_id):
    if request.user.role != 'admin':
        return redirect('home')
    property = get_object_or_404(Property, id=property_id)
    return render(request, 'property_detail.html', {'property': property})

# Property Actions
@login_required
def edit_property(request, property_id):
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    if property.status == 'sold':
        messages.error(request, "Cannot edit a sold property.")
        return redirect('user_properties')
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property)
        if form.is_valid():
            updated_property = form.save(commit=False)
            # Reset status to 'pending' for admin approval after update
            updated_property.status = 'pending'
            updated_property.save()
            messages.success(request, "Property updated and submitted for admin approval.")
            return redirect('user_properties')
    else:
        form = PropertyForm(instance=property)
    return render(request, 'edit_property.html', {'form': form, 'property': property})

@login_required
def delete_property(request, property_id):
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    if property.status == 'sold':
        messages.error(request, "Cannot delete a sold property.")
        return redirect('user_properties')
    if request.method == 'POST':
        property.delete()
        messages.success(request, "Property deleted successfully.")
        return redirect('user_properties')
    return render(request, 'delete_property.html', {'property': property})

@login_required
def view_property(request, property_id):
    property = get_object_or_404(Property, id=property_id, seller=request.user)
    return render(request, 'property_detail.html', {'property': property})

# New: Admin view for agent assignments
@login_required
def admin_agent_assignments(request):
    if request.user.role != 'admin':
        return redirect('home')
    # Changed: Annotate agents with active properties and attach filtered properties directly
    agents = CustomUser.objects.filter(role='agent').annotate(
        active_properties=models.Count('properties', filter=models.Q(properties__status__in=['pending', 'approved']))
    )
    # New: Attach filtered properties to each agent object
    for agent in agents:
        agent.active_property_list = agent.properties.filter(status__in=['pending', 'approved'])
    return render(request, 'admin_agent_assignments.html', {'agents': agents})


@login_required
def remove_interest(request, property_id):
    property = get_object_or_404(Property, id=property_id, status='approved')
    if request.user != property.seller and request.user.role == 'normal':
        Interest.objects.filter(property=property, interested_user=request.user).delete()
        messages.success(request, "Interest removed successfully.")
    return redirect('home')

#Request Transaction

@login_required
def request_transaction(request, property_id):
    if request.user.role != 'agent':
        messages.error(request, "Only agents can request transactions.")
        return redirect('home')
    
    property = get_object_or_404(Property, id=property_id, interest__assigned_agent=request.user)
    if property.status == 'sold':
        messages.error(request, "This property is already sold.")
        return redirect('agent_properties')

    if request.method == 'POST':
        buyer_id = request.POST.get('buyer_id')
        buyer = get_object_or_404(CustomUser, id=buyer_id)
        amount = request.POST.get('amount')
        
        # Updated: Create transaction request
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

    # Get interested users for this property
    interested_users = Interest.objects.filter(property=property, assigned_agent=request.user, status='assigned')
    return render(request, 'request_transaction.html', {
        'property': property,
        'interested_users': interested_users
    })


# properties/views.py
@login_required
def admin_confirm_transaction(request, transaction_id):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can confirm transactions.")
        return redirect('home')
    
    transaction = get_object_or_404(Transaction, id=transaction_id, payment_status='pending')
    if request.method == 'POST':
        # Updated: Confirm transaction and mark property as sold
        transaction.payment_status = 'approved'
        transaction.property.status = 'sold'
        transaction.property.save()
        transaction.save()
        messages.success(request, f"Transaction for '{transaction.property.title}' confirmed.")
        return redirect('admin_transactions')
    
    return render(request, 'admin_confirm_transaction.html', {'transaction': transaction})