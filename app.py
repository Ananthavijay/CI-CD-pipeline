from . import app, db
from flask import request, make_response
from .models import Users, Notes
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps

with app.app_context():
    db.create_all()

@app.route("/signup", methods=["POST"])
def signup():
	data = request.json
	email = data.get("email")
	firstName = data.get("firstName")
	lastName = data.get("lastName")
	password = data.get("password")

	if firstName and lastName and email and password:
		user = Users.query.filter_by(email=email).first()
		if user:
			return make_response(
				{"message": "Please Sign In"},
				200
			)

		user = Users(
			email = email,
			password = generate_password_hash(password),
			firstName = firstName,
			lastName = lastName
		)
		db.session.add(user)
		db.session.commit()
		return make_response(
			{"message": "User Created"},
			201
		)

	return make_response(
		{"message": "Unable to create User"},
		500
	)


@app.route("/login", methods=["POST"])
def login():
	auth = request.json
	if not auth or not auth.get("email") or not auth.get("password"):
		return make_response(
			{"message": "Proper credentials were not provided"},
			401
		)
	user = Users.query.filter_by(email=auth.get("email")).first()
	if not user:
		return make_response(
			{"message": "Please create an account"},
			401
		)
	if check_password_hash(user.password, auth.get("password")):
		token = jwt.encode({
			'id': user.id,
			'exp': datetime.utcnow() + timedelta(minutes=30)
			},
			"secret",
			"HS256"
		)
		return make_response({"token": token},201)

	return make_response(
			{"message": "Please check your credentials"},
			401
		)

def token_required(f):
	
	@wraps(f)
	def decorated(*args, **kwargs):
		token = None
		if 'Authorization' in request.headers:
			token = request.headers['Authorization']
		if not token:
			return make_response(
				{"message": "Token is missing"},
				401
			)

		try:
			data = jwt.decode(token, "secret", algorithms=["HS256"])
			current_user = Users.query.filter_by(id=data["id"]).first()
		except Exception as e:
			print(e)
			return make_response(
				{"message": "Token is invalid"},
				401
			)
		return f(current_user, *args, **kwargs)
	return decorated

@app.route("/notes", methods=["GET"])
@token_required
def getAllNotes(current_user):
	notes = Notes.query.filter_by(userId=current_user.id).all()
	totalNotes = 0
	if notes:
		totalNotes = Notes.query.filter_by(userId=current_user.id).count()
	return make_response({
		"data": [note.serialize for note in notes],
		"total": totalNotes
	})

@app.route("/notes", methods=["POST"])
@token_required
def createNote(current_user):
	data = request.json
	content = data.get("content")
	if content:
		note = Notes(
			content = content,
			userId = current_user.id
		)
		db.session.add(note)
		db.session.commit()
	return note.serialize

@app.route("/notes/<id>", methods=["PUT"])
@token_required
def updateNote(current_user,id):
	try:
		note = Notes.query.filter_by(userId=current_user.id, id=id).first()
		if note == None:
			return make_response({"message": f"Note with {id} not found"}, 404)
		data = request.json
		content = data.get("content")
		if content:
			note.content = content
		db.session.commit()
		return make_response({"message": note.serialize}, 200)
	except Exception as e:
		print(e)
		return make_response({"message": "Unable to process"}, 409)


@app.route("/notes/<id>", methods=["DELETE"])
@token_required
def deleteNote(current_user,id):
	try:
		note = Notes.query.filter_by(userId=current_user.id, id=id).first()
		if note == None:
			return make_response({"message": f"Note with {id} not found"}, 404)
		db.session.delete(note)
		db.session.commit()
		return make_response({"message": "Deleted"}, 202)
	except Exception as e:
		print(e)
		return make_response({"message": "Unable to process"}, 409)