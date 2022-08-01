from frontend.models import Step, Flowchart

allObjects = Step.objects.all()
allFields = Step._meta.get_fields()
print(allObjects)
for i in range(Flowchart.objects.all().count()):
    print(Flowchart.objects.all()[i].step_set.all())
    allSteps = Flowchart.objects.all()[i]
    print(allSteps.step_set.all())


# print(allObjects)
# print(allObjects.count())
# for i in range(allObjects.count()):
#     print(allObjects[i].name)
#     print(allObjects[i].id)
#     print(allObjects[i].flowchart)
#     if(allObjects[i].parentId == None):
#         print("None")
#     else:
#         print(allObjects[i].parentId.id)
#     print()
