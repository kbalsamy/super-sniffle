# GoF Design Patterns (23) — Java Quick Reference

## Creational (5)

| Pattern | Intent | Analogy | Java Example |
|---|---|---|---|
| Singleton | One instance, global access | There's only one President at a time | `class DB { private static DB inst; private DB(){} static DB get(){ if(inst==null) inst=new DB(); return inst; } }` |
| Factory Method | Subclass decides which class to instantiate | Ordering "coffee" at a cafe — barista picks the recipe | `abstract class Dialog { abstract Button createButton(); }` `class WinDialog extends Dialog { Button createButton(){ return new WinButton(); } }` |
| Abstract Factory | Family of related objects without specifying concrete classes | Furniture store selling matching sofa+chair sets per style (Victorian/Modern) | `interface GUIFactory { Button createButton(); Checkbox createCheckbox(); }` |
| Builder | Construct complex object step by step | Ordering a custom sandwich (bread, filling, sauce chosen one by one) | `Pizza p = new Pizza.Builder().size(12).cheese(true).build();` |
| Prototype | Copy existing object instead of building new | Photocopying a signed contract instead of rewriting it | `class Sheep implements Cloneable { public Sheep clone(){ return (Sheep) super.clone(); } }` |

## Structural (7)

| Pattern | Intent | Analogy | Java Example |
|---|---|---|---|
| Adapter | Convert one interface into another expected one | Plug adapter for a EU charger into a US socket | `class SocketAdapter implements USB { EUPlug plug; void connect(){ plug.connectEU(); } }` |
| Bridge | Decouple abstraction from implementation so both vary independently | TV remote (abstraction) works with any TV brand (implementation) | `abstract class Shape { Renderer r; abstract void draw(); }` |
| Composite | Treat individual objects and groups uniformly (tree structure) | A folder containing files and other folders, all "openable" | `interface FileSystemItem { void show(); }` `class Folder implements FileSystemItem { List<FileSystemItem> children; }` |
| Decorator | Add behavior to an object dynamically, without subclassing | Adding toppings to a base pizza, each wraps and adds cost | `Coffee c = new MilkDecorator(new SugarDecorator(new SimpleCoffee()));` |
| Facade | Simple unified interface over a complex subsystem | Car's ignition button hides engine, fuel, battery startup logic | `class ComputerFacade { void start(){ cpu.boot(); mem.load(); disk.read(); } }` |
| Flyweight | Share common state across many objects to save memory | Chess pieces of the same color/type share one icon object | `class GlyphFactory { Map<Character,Glyph> cache; Glyph get(char c){ return cache.computeIfAbsent(c, Glyph::new); } }` |
| Proxy | Placeholder controlling access to another object | A credit card is a proxy for your bank account | `class ImageProxy implements Image { RealImage real; void display(){ if(real==null) real=new RealImage(); real.display(); } }` |

## Behavioral (11)

| Pattern | Intent | Analogy | Java Example |
|---|---|---|---|
| Chain of Responsibility | Pass request along a chain until someone handles it | Tech support: L1 escalates to L2, L2 to L3 | `abstract class Handler { Handler next; void handle(Req r){ if(next!=null) next.handle(r); } }` |
| Command | Encapsulate a request as an object | A restaurant order slip — decouples waiter from chef | `interface Command { void execute(); }` `class LightOnCommand implements Command { void execute(){ light.on(); } }` |
| Interpreter | Define grammar and interpret sentences in it | A calculator parsing "3 + 4 * 2" | `interface Expr { int interpret(); }` `class Add implements Expr { Expr l,r; int interpret(){ return l.interpret()+r.interpret(); } }` |
| Iterator | Access elements sequentially without exposing structure | A TV remote's "next channel" button, regardless of how channels are stored | `Iterator<String> it = list.iterator(); while(it.hasNext()) print(it.next());` |
| Mediator | Centralize complex communication between objects | Air traffic control coordinating planes instead of planes talking directly | `class ChatMediator { void send(String msg, User from){ users.forEach(u -> { if(u!=from) u.receive(msg); }); } }` |
| Memento | Capture and restore an object's state (undo) | Ctrl+Z in a text editor | `class Memento { private final String state; Memento(String s){state=s;} String get(){return state;} }` |
| Observer | Notify dependents automatically on state change | Subscribing to a YouTube channel — upload notifies all subscribers | `subject.addObserver(o); subject.setState(x); // notifies all observers` |
| State | Change behavior when internal state changes | A traffic light behaves differently in Red/Yellow/Green state | `interface State { void handle(Context c); }` `class RedState implements State { void handle(Context c){ c.setState(new GreenState()); } }` |
| Strategy | Swap algorithms interchangeably at runtime | Choosing "walk / bike / car" for the same trip | `interface SortStrategy { void sort(int[] a); }` `context.setStrategy(new QuickSort()); context.sort(arr);` |
| Template Method | Skeleton of algorithm in base class, steps overridden by subclasses | A recipe outline: boil water → add ingredient (varies) → serve | `abstract class Game { final void play(){ init(); start(); end(); } abstract void init(); }` |
| Visitor | Add new operations to a class hierarchy without changing it | An auditor visiting each department, applying the same "audit" operation | `interface Visitor { void visit(Book b); void visit(CD c); }` `class Book { void accept(Visitor v){ v.visit(this); } }` |

---
**Caveat (per Core Java / Cay Horstmann):** many of these predate Java 8 lambdas. Strategy, Command, Observer, and Iterator are often better expressed today with functional interfaces (`Runnable`, `Comparator`, `Consumer`, streams) instead of full class hierarchies — less boilerplate, same intent.
