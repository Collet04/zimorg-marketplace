from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def home_view(request):
    # Route sellers straight to their seller dashboard
    if request.user.is_seller():
        return redirect('sellers:dashboard')
    
    # Regular buyers or other roles go to general homepage
    return render(request, 'dashboard/home.html')