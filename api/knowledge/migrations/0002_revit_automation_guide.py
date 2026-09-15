"""Seeds the first Knowledge Base guide: getting into Revit automation.

Editable afterwards in /admin (Knowledge Base & Legal Pages → Articles).
Re-running replaces the sections of this one article only.
"""
from django.db import migrations

SLUG = "getting-started-with-revit-automation"

JOIN_TWO_CODE = """using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;

namespace JoinTool
{
    [Transaction(TransactionMode.Manual)]
    public class JoinTwoElementsCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uiDoc = commandData.Application.ActiveUIDocument;
            Document doc = uiDoc.Document;

            try
            {
                // 1. Ask the user to click two elements.
                Reference firstRef = uiDoc.Selection.PickObject(ObjectType.Element, "Pick the first element");
                Reference secondRef = uiDoc.Selection.PickObject(ObjectType.Element, "Pick the second element");

                Element first = doc.GetElement(firstRef);
                Element second = doc.GetElement(secondRef);

                // 2. Nothing to do if they're already joined.
                if (JoinGeometryUtils.AreElementsJoined(doc, first, second))
                {
                    TaskDialog.Show("Join Tool", "These elements are already joined.");
                    return Result.Succeeded;
                }

                // 3. Every change to the model happens inside a transaction.
                using (Transaction tx = new Transaction(doc, "Join Two Elements"))
                {
                    tx.Start();
                    JoinGeometryUtils.JoinGeometry(doc, first, second);
                    tx.Commit();
                }

                return Result.Succeeded;
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                // The user pressed Esc while picking.
                return Result.Cancelled;
            }
            catch (Autodesk.Revit.Exceptions.ArgumentException ex)
            {
                // Revit refuses to join elements that don't touch or can't be joined.
                message = "These elements can't be joined: " + ex.Message;
                return Result.Failed;
            }
        }
    }
}"""

CSPROJ_CODE = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <!-- Revit 2025 and newer: net8.0-windows. Revit 2024 and older: net48. -->
    <TargetFramework>net8.0-windows</TargetFramework>
  </PropertyGroup>

  <ItemGroup>
    <Reference Include="RevitAPI">
      <HintPath>C:\\Program Files\\Autodesk\\Revit 2025\\RevitAPI.dll</HintPath>
      <Private>false</Private>
    </Reference>
    <Reference Include="RevitAPIUI">
      <HintPath>C:\\Program Files\\Autodesk\\Revit 2025\\RevitAPIUI.dll</HintPath>
      <Private>false</Private>
    </Reference>
  </ItemGroup>
</Project>"""

ADDIN_CODE = """<?xml version="1.0" encoding="utf-8"?>
<RevitAddIns>
  <AddIn Type="Command">
    <Name>Join Two Elements</Name>
    <Text>Join Two Elements</Text>
    <Assembly>C:\\RevitPlugins\\JoinTool\\JoinTool.dll</Assembly>
    <FullClassName>JoinTool.JoinTwoElementsCommand</FullClassName>
    <!-- Generate your own GUID: Visual Studio > Tools > Create GUID -->
    <AddInId>8D83F3B4-6C1A-4F2E-9B7D-2E5A1C4F9A10</AddInId>
    <VendorId>JOINTOOL</VendorId>
    <VendorDescription>Your name or company</VendorDescription>
  </AddIn>
</RevitAddIns>"""

JOIN_SELECTED_CODE = """using System.Collections.Generic;
using System.Linq;
// ...plus the same Autodesk.Revit usings as before

ICollection<ElementId> selectedIds = uiDoc.Selection.GetElementIds();
List<Element> selected = selectedIds.Select(id => doc.GetElement(id)).ToList();
int joinedPairs = 0;

using (Transaction tx = new Transaction(doc, "Join Selected Elements"))
{
    tx.Start();

    // Try every pair once: (0,1), (0,2), (1,2), ...
    for (int i = 0; i < selected.Count; i++)
    {
        for (int j = i + 1; j < selected.Count; j++)
        {
            Element a = selected[i];
            Element b = selected[j];
            if (JoinGeometryUtils.AreElementsJoined(doc, a, b)) continue;

            try
            {
                JoinGeometryUtils.JoinGeometry(doc, a, b);
                joinedPairs++;
            }
            catch (Autodesk.Revit.Exceptions.ArgumentException)
            {
                // Not touching, or not a joinable pair: skip it.
            }
        }
    }

    tx.Commit();
}

TaskDialog.Show("Join Tool", $"Joined {joinedPairs} pair(s).");"""

AI_PROMPT_CODE = """I'm writing a Revit 2025 add-in in C# (.NET 8).
Write an IExternalCommand that joins every pair of elements in the
current selection using JoinGeometryUtils.

Requirements:
- Skip pairs that are already joined or can't be joined.
- Make all changes inside a single Transaction.
- Show a TaskDialog with how many pairs were joined.
- Explain each Revit API call you use in one line, and tell me
  if any of them changed between Revit versions."""

SECTIONS = [
    {
        "title": "What is Revit automation?",
        "body": (
            "Most of the time in Revit goes to repeating the same clicks: joining walls to floors, "
            "renaming views, filling in parameters, placing tags. Revit automation means writing a small "
            "program that does those clicks for you.\n\n"
            "These programs are called add-ins or plugins. They show up inside Revit like any other tool, "
            "usually as a button on the Add-Ins tab. Every plugin sold on BIMHIVE started as exactly this: "
            "someone got tired of a repetitive task and automated it.\n\n"
            "This guide walks you from zero to a working plugin: how Revit exposes itself to code, which "
            "language to use, how to set up your computer, and a complete Join tool you can build today. "
            "At the end we look at how AI can speed this up, and how to use it safely."
        ),
    },
    {
        "title": "How Revit works under the hood",
        "body": (
            "A Revit model is a database of elements. A wall, a door, a view, a sheet and a level are all "
            "elements. Each one has a unique ElementId, belongs to a category (Walls, Doors, Views...), and "
            "stores its information in parameters (Length, Mark, Comments...).\n\n"
            "Autodesk gives developers access to this database through the Revit API: a set of .NET "
            "libraries that ship with every Revit installation. The two you use in almost every plugin are "
            "RevitAPI.dll (the model: elements, geometry, parameters) and RevitAPIUI.dll (the user "
            "interface: selection, dialogs, ribbon buttons).\n\n"
            "A few ideas you will meet constantly:\n"
            "- Document: the open model file.\n"
            "- UIDocument: the same model plus what the user sees and has selected.\n"
            "- FilteredElementCollector: how you search the model, for example \"all walls on Level 1\".\n"
            "- Transaction: Revit only lets you change the model inside a transaction. Reading doesn't need "
            "one; creating, deleting or editing anything does. A transaction is also what appears in the "
            "Undo list.\n\n"
            "Revit runs your code on its own main thread, while the user waits. So a plugin should do its "
            "work and finish, not run forever in the background."
        ),
    },
    {
        "title": "Which programming language does Revit use?",
        "body": (
            "The Revit API is built on .NET, Microsoft's development platform. Any .NET language can use "
            "it, but in practice almost everyone uses C#. Nearly all documentation, samples and forum "
            "answers are written in C#, so that's the one to learn.\n\n"
            "The .NET version depends on your Revit version, and this matters when you create a project:\n"
            "- Revit 2025 and newer run on .NET 8.\n"
            "- Revit 2021 to 2024 run on .NET Framework 4.8.\n"
            "A plugin built for one of these generations won't load in the other, which is why plugins are "
            "usually built separately for each Revit year.\n\n"
            "There are other ways in, too:\n"
            "- Dynamo, Revit's built-in visual programming tool. You connect nodes instead of writing code. "
            "It's great for learning how the API thinks, and it can run Python.\n"
            "- pyRevit, a free community toolkit that lets you write tools in Python.\n\n"
            "Python is quicker to start with, but compiled C# plugins are faster, easier to distribute, and "
            "what commercial plugins use. This guide uses C#."
        ),
    },
    {
        "title": "Setting up your computer",
        "body": (
            "You need three things, all free apart from Revit itself:\n"
            "1. Revit installed (any recent version; this guide uses 2025).\n"
            "2. Visual Studio 2022 Community, with the \".NET desktop development\" workload.\n"
            "3. A new C# Class Library project. A class library builds a .dll file, which is what Revit loads.\n\n"
            "In the project, add references to RevitAPI.dll and RevitAPIUI.dll from Revit's install folder. "
            "Set them to not be copied to your output folder: Revit already has them loaded, and shipping "
            "your own copies causes conflicts.\n\n"
            "The project file below does all of this for Revit 2025. For Revit 2024 or older, change the "
            "target framework to net48 and point the paths at that Revit year's folder."
        ),
        "code": CSPROJ_CODE,
        "code_language": "xml",
    },
    {
        "title": "The anatomy of a plugin",
        "body": (
            "The simplest kind of plugin is an external command: a class that implements the "
            "IExternalCommand interface. It has one method, Execute, which Revit calls when the user "
            "clicks your button.\n\n"
            "Execute receives the running Revit application (through ExternalCommandData) and returns a "
            "Result: Succeeded, Cancelled, or Failed. If you return Failed, whatever you put in the "
            "message parameter is shown to the user.\n\n"
            "The [Transaction(TransactionMode.Manual)] attribute on the class tells Revit that you will "
            "open your own transactions when you need them. That's the mode you'll almost always use.\n\n"
            "Revit also needs to know your plugin exists. That's the job of a small .addin manifest file, "
            "covered in a later section."
        ),
    },
    {
        "title": "Build it: a Join tool",
        "body": (
            "Revit's Join Geometry command makes overlapping elements, such as a wall and a floor, share "
            "clean geometry. Doing it by hand means clicking the command, then both elements, again and "
            "again. Let's build our own version.\n\n"
            "The API side is a class called JoinGeometryUtils. We'll use two of its methods: "
            "AreElementsJoined, to check first, and JoinGeometry, to do the join.\n\n"
            "The command below asks the user to pick two elements, checks whether they're already joined, "
            "then joins them inside a transaction. It also handles the two things that go wrong in real "
            "use: the user pressing Esc while picking, and Revit refusing to join elements that don't "
            "touch.\n\n"
            "Create a file called JoinTwoElementsCommand.cs in your project and paste this in:"
        ),
        "code": JOIN_TWO_CODE,
        "code_language": "csharp",
    },
    {
        "title": "Tell Revit about your plugin",
        "body": (
            "Revit loads plugins listed in .addin manifest files. Save the file below as JoinTool.addin in "
            "one of these folders (replace 2025 with your Revit year):\n"
            "- Just for you: %AppData%\\Autodesk\\Revit\\Addins\\2025\\\n"
            "- For everyone on the computer: C:\\ProgramData\\Autodesk\\Revit\\Addins\\2025\\\n\n"
            "Assembly is the full path to the .dll you built. FullClassName is your namespace plus class "
            "name. AddInId must be a GUID that is unique to your plugin, so generate a new one rather than "
            "copying the one shown here.\n\n"
            "Build the project, start Revit, and open a model. The first time, Revit asks whether to load "
            "the add-in; choose Always Load. Your command appears under Add-Ins → External Tools."
        ),
        "code": ADDIN_CODE,
        "code_language": "xml",
    },
    {
        "title": "Testing and debugging",
        "body": (
            "To step through your code line by line, start Revit, then in Visual Studio use Debug → Attach "
            "to Process and pick Revit.exe. Put a breakpoint inside Execute and run your command.\n\n"
            "Things that trip up almost everyone at first:\n"
            "- Revit locks your .dll while it's running, so close Revit before you rebuild.\n"
            "- \"Modifying is forbidden because the document has no open transaction\" means you changed "
            "the model outside a transaction.\n"
            "- If your button doesn't appear, check the Assembly path and FullClassName in the .addin file "
            "first. A typo there fails silently.\n\n"
            "Always test on a copy of a real project, never on live work. Ctrl+Z undoes a committed "
            "transaction, but a copy is safer while you're learning."
        ),
    },
    {
        "title": "Make it more useful: join everything you select",
        "body": (
            "Picking two elements at a time is only slightly faster than the built-in command. The real win "
            "is joining a whole selection at once.\n\n"
            "This version reads the user's current selection and tries to join every pair. Pairs that "
            "don't touch are skipped instead of stopping the command, and everything happens in one "
            "transaction, so a single Ctrl+Z undoes the lot. Replace the body of Execute with this "
            "(keep the try/catch for cancellation):"
        ),
        "code": JOIN_SELECTED_CODE,
        "code_language": "csharp",
    },
    {
        "title": "Let AI help you write the code",
        "body": (
            "AI assistants like Claude or ChatGPT are genuinely useful for Revit development. They can "
            "write a first draft of a command, explain an API class you haven't seen before, turn an error "
            "message into a likely cause, or convert a Dynamo graph into C#.\n\n"
            "The quality of the answer depends on the question. Always tell it your Revit version, that "
            "you're using C#, and exactly what the tool should do, including the edge cases. For example:"
        ),
        "code": AI_PROMPT_CODE,
        "code_language": "text",
    },
    {
        "title": "Review everything the AI writes",
        "body": (
            "AI makes you faster, but you are still the developer. It can be confidently wrong, and a "
            "plugin runs on real project files. Before you trust generated code:\n\n"
            "1. Read it line by line until you understand it. If you can't explain a line, ask the AI to "
            "explain it, then check that explanation against the official Revit API documentation.\n"
            "2. Check that every class and method actually exists in your Revit version. AI sometimes "
            "invents API calls that look plausible, or uses ones that were renamed or removed.\n"
            "3. Make sure every change to the model is inside a transaction.\n"
            "4. Look for missing error handling: what happens if the selection is empty, the user presses "
            "Esc, or an element is in a linked model?\n"
            "5. Test it on a copy of a real project, including awkward cases, before you use it on live work.\n"
            "6. Don't paste confidential client information or project data into an AI tool.\n\n"
            "A good rhythm is: ask for a small piece, read it, run it, then ask for the next piece. You'll "
            "learn the API much faster that way than by pasting in one huge program."
        ),
    },
    {
        "title": "Where to go next",
        "body": (
            "Once your Join tool works, try:\n"
            "- Adding a proper ribbon button with an icon (look up IExternalApplication and RibbonPanel).\n"
            "- Using FilteredElementCollector to find elements automatically instead of asking the user to pick.\n"
            "- Building a small window for settings with WPF.\n\n"
            "Useful places to keep learning: the official Revit API documentation from Autodesk, the Revit "
            "API forum on the Autodesk Community site, the long-running \"The Building Coder\" blog, and the "
            "SDK samples in the Revit SDK download.\n\n"
            "And when you've built something other Revit users would pay for, you can sell it here: see "
            "Sell on BIMHIVE."
        ),
    },
]


def seed_guide(apps, schema_editor):
    Article = apps.get_model("knowledge", "Article")
    ArticleSection = apps.get_model("knowledge", "ArticleSection")
    article, _ = Article.objects.update_or_create(
        slug=SLUG,
        defaults={
            "kind": "knowledge",
            "title": "Getting Started with Revit Automation",
            "summary": (
                "How Revit works under the hood, which language and .NET version to use, how to build "
                "your first plugin (a Join tool), and how to use AI to help you write it safely."
            ),
            "is_published": True,
            "sort_order": 0,
        },
    )
    ArticleSection.objects.filter(article=article).delete()
    for order, section in enumerate(SECTIONS):
        ArticleSection.objects.create(
            article=article,
            sort_order=order,
            title=section["title"],
            body=section["body"],
            code=section.get("code", ""),
            code_language=section.get("code_language", ""),
        )


def remove_guide(apps, schema_editor):
    apps.get_model("knowledge", "Article").objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0001_initial")]

    operations = [migrations.RunPython(seed_guide, remove_guide)]
