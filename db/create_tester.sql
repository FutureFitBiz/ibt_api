use ibt;
delete from user where email='tester@futurefitbusiness.org';
insert into user(first, email, password, admin)
values ( 'Tester', 'tester@futurefitbusiness.org', '$2b$12$FGxUfHcVWTQGOKaA2HQQn.T2cEMt.1q2vf2XtIYrP2XWw/bwjEY62', true);
