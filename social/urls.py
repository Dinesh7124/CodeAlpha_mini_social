from django.urls import path
from . import views

urlpatterns = [
    # ============ AUTH ============
    path('', views.feed, name='feed'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('api/friends/', views.api_friends, name='api_friends'),
    # ============ FORGOT PASSWORD ============
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('run-migrations/', views.run_migrations, name='run_migrations'),
    # ============ PROFILE ============
    path('profile/<str:username>/', views.profile, name='profile'),
    path('settings/profile/', views.edit_profile, name='edit_profile'),
    path('profile-viewers/', views.profile_viewers, name='profile_viewers'),

    # ============ NOTIFICATIONS / SEARCH ============
    path('notifications/', views.notifications, name='notifications'),
    path('search/', views.search, name='search'),

    # ============ POSTS ============
    path('api/post/', views.create_post, name='create_post'),
    path('api/post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('api/post/<int:post_id>/delete/', views.delete_post, name='delete_post'),

    # ============ LIKE / REACTION / COMMENT ============
    path('api/like/<int:post_id>/', views.toggle_like, name='toggle_like'),
    path('api/reaction/<int:post_id>/', views.toggle_reaction, name='toggle_reaction'),
    path('api/comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # ============ FOLLOW ============
    path('api/follow/<str:username>/', views.toggle_follow, name='toggle_follow'),

    # ============ FRIEND REQUESTS ============
    path('friend-request/send/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friend-request/accept/<int:req_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('friend-request/reject/<int:req_id>/', views.reject_friend_request, name='reject_friend_request'),
    path('friend-requests/', views.friend_requests_list, name='friend_requests_list'),
    path('friends/', views.friends_list, name='friends_list'),

    # ============ CHAT ============
    path('inbox/', views.inbox, name='inbox'),
    path('chat/start/<int:user_id>/', views.start_chat, name='start_chat'),
    path('chat/<int:conv_id>/', views.chat_room, name='chat_room'),
    path('chat/<int:conv_id>/send/', views.chat_send_message, name='chat_send_message'),
    path('chat/<int:conv_id>/new/', views.get_new_messages, name='get_new_messages'),
    path('chat/<int:conv_id>/typing/', views.chat_typing, name='chat_typing'),

    # ============ STORIES ============
    path('stories/', views.stories_view, name='stories'),
    path('stories/create/', views.create_story, name='create_story'),

    # ============ SAVED POSTS ============
    path('saved/', views.saved_posts, name='saved_posts'),
    path('api/save/<int:post_id>/', views.toggle_save, name='toggle_save'),

    # ============ SUGGESTIONS + LIVE UNREAD ============
    path('api/suggestions/', views.suggestions, name='suggestions'),
    path('api/unread/', views.unread_count, name='unread_count'),

    # ============ PHASE 1 FEATURES ============
    path('api/share/<int:post_id>/', views.share_post, name='share_post'),
    path('api/story/<int:story_id>/react/', views.react_story, name='react_story'),
    path('api/block/<str:username>/', views.toggle_block, name='toggle_block'),
    path('api/report/', views.report_content, name='report_content'),
    path('explore/', views.hashtag_explore, name='explore'),
    path('explore/<str:tag>/', views.hashtag_explore, name='hashtag_posts'),

    # ============ ADMIN PANEL ============
    path('panel/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/users/', views.admin_users, name='admin_users'),
    path('panel/users/<int:user_id>/role/', views.admin_change_role, name='admin_change_role'),
    path('panel/users/<int:user_id>/ban/', views.admin_toggle_ban, name='admin_toggle_ban'),
    path('panel/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('panel/posts/', views.admin_posts, name='admin_posts'),
    path('panel/posts/<int:post_id>/delete/', views.admin_delete_post, name='admin_delete_post'),
    path('panel/comments/', views.admin_comments, name='admin_comments'),
    path('panel/comments/<int:comment_id>/delete/', views.admin_delete_comment, name='admin_delete_comment'),
    path('panel/messages/', views.admin_messages, name='admin_messages'),
    path('panel/activity/', views.admin_activity, name='admin_activity'),
]